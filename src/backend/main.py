import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from braintrust import update_span
from src.backend.agent.runner import resolve_agent_framework, run_agent_turn
from src.backend.agent.tracing import build_callback_handler, init_tracing
from src.backend.api.models import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    UploadResponse,
)
from src.backend.storage.session_store import SessionStore

load_dotenv()
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = init_tracing()
    session_store = SessionStore()
    app.state.logger = logger
    app.state.session_store = session_store
    yield
    if hasattr(logger, "flush"):
        logger.flush()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/frameworks")
def frameworks() -> dict:
    return {
        "active": resolve_agent_framework(),
        "supported": ["langgraph", "openai_agents", "google_adk"],
    }


def _handle_chat_turn(
    conversation_id: str,
    thread_id: str,
    message: str,
    document_path: str | None,
    logger,
    root_parent: str | None,
    framework: str,
):
    handler = build_callback_handler(logger)
    with logger.start_span(name="chat_turn", parent=root_parent) as span:
        turn = run_agent_turn(
            framework=framework,
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_message=message,
            document_path=document_path,
            model_name=os.getenv("DEFAULT_LLM_MODEL"),
            callbacks=[handler],
            metadata={
                "conversation_id": conversation_id,
                "thread_id": thread_id,
                "document_path": document_path,
                "agent_framework": framework,
            },
        )
        span.log(
            metadata={
                "conversation_id": conversation_id,
                "thread_id": thread_id,
                "agent_framework": framework,
            }
        )
        span.log(
            input={
                "conversation_id": conversation_id,
                "thread_id": thread_id,
                "message": message,
                "document_path": document_path,
            },
            output={
                "assistant_message": turn.assistant_message,
            },
        )
    span_export = span.export()
    return turn, span.span_id, span_export


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    session_store = app.state.session_store
    logger = app.state.logger
    session = session_store.get_or_create_session(request.conversation_id)
    root_span_export = session.root_span_export or None
    root_span_id = session.root_span_id or None
    created_root = False
    framework = resolve_agent_framework()
    thread_id = session.thread_id or str(uuid.uuid4())
    if session.thread_id is None:
        session_store.update_thread_id(request.conversation_id, thread_id)

    if not root_span_export or not root_span_id:
        with logger.start_span(name="Rev Agent") as root_span:
            root_span.log(
                metadata={
                    "conversation_id": request.conversation_id,
                    "thread_id": thread_id,
                    "agent_framework": framework,
                }
            )
            root_span_id = root_span.root_span_id
        root_span_export = root_span.export()
        session_store.update_root_span(
            conversation_id=request.conversation_id,
            root_span_id=root_span_id,
            root_span_export=root_span_export,
        )
        created_root = True
        logging.getLogger(__name__).info(
            "Created root span conversation_id=%s root_span_id=%s export_len=%s export_prefix=%s",
            request.conversation_id,
            root_span_id,
            len(root_span_export or ""),
            (root_span_export or "")[:12],
        )

    turn, span_id, span_export = _handle_chat_turn(
        conversation_id=request.conversation_id,
        thread_id=thread_id,
        message=request.message,
        document_path=session.document_path,
        logger=logger,
        root_parent=root_span_export,
        framework=framework,
    )

    logging.getLogger(__name__).info(
        "Using root span for conversation_id=%s root_span_id=%s export_len=%s",
        request.conversation_id,
        root_span_id,
        len(root_span_export or ""),
    )

    assistant_message = turn.assistant_message
    transcript = session.transcript or []
    input_messages = transcript + [{"role": "user", "content": request.message}]
    output_messages = input_messages + [
        {"role": "assistant", "content": assistant_message}
    ]
    session_store.update_transcript(request.conversation_id, output_messages)

    if root_span_export:
        if created_root:
            logger.flush()
        try:
            update_span(
                root_span_export,
                input={"messages": input_messages},
                output={"messages": output_messages},
                metadata={
                    "conversation_id": request.conversation_id,
                    "thread_id": thread_id,
                    "agent_framework": framework,
                },
            )
            logger.flush()
            logging.getLogger(__name__).info(
                "Updated root span input/output conversation_id=%s messages_in=%s messages_out=%s export_prefix=%s",
                request.conversation_id,
                len(input_messages),
                len(output_messages),
                (root_span_export or "")[:12],
            )
        except Exception as exc:
            logging.getLogger(__name__).exception(
                "Failed to update root span conversation_id=%s root_span_id=%s: %s",
                request.conversation_id,
                root_span_id,
                exc,
            )
    return ChatResponse(
        conversation_id=request.conversation_id,
        assistant_message=assistant_message,
        span_id=span_id,
        root_span_id=root_span_id,
    )


@app.post("/upload", response_model=UploadResponse)
def upload(
    conversation_id: str = Form(...), file: UploadFile = File(...)
) -> UploadResponse:
    session_store = app.state.session_store
    logger = app.state.logger
    session_store.get_or_create_session(conversation_id)
    uploads_dir = os.getenv("UPLOADS_DIR", "./data/uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    safe_name = file.filename or "document.txt"
    document_id = f"{uuid.uuid4()}_{safe_name}"
    file_path = os.path.join(uploads_dir, document_id)
    with open(file_path, "wb") as handle:
        handle.write(file.file.read())

    session_store.update_document_path(conversation_id, file_path)
    return UploadResponse(
        status="ok",
        conversation_id=conversation_id,
        document_id=document_id,
    )


@app.post("/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    if request.rating is None and not request.comment:
        raise HTTPException(
            status_code=400, detail="rating or comment must be provided"
        )
    scores = None
    tags = None
    if request.rating in {"up", "down"}:
        score_value = 1.0 if request.rating == "up" else 0.0
        scores = {"thumbs_up": score_value}
        tags = [f"thumbs_{request.rating}"]
    logger = app.state.logger
    logger.log_feedback(
        id=request.span_id,
        scores=scores,
        comment=request.comment,
        tags=tags,
    )
    return FeedbackResponse(status="ok")



    
