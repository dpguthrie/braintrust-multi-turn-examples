from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from src.backend.agent.prompts import build_summarizer_prompt
from src.backend.agent.tools import rag_tool, web_search_tool
from src.backend.agent.types import AgentTurnResult

_APP_NAME = "rev-langgraph-example"
_ADK_SESSION_SERVICE = None
_ADK_RUNNERS: dict[str, Any] = {}
_ADK_SESSIONS_CREATED: set[tuple[str, str]] = set()


def _google_adk_imports():
    try:
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types as genai_types
    except ImportError as exc:
        raise RuntimeError(
            "Google ADK is not installed. Install with: uv sync --extra google-adk"
        ) from exc
    return LlmAgent, Runner, InMemorySessionService, genai_types


def _instructions() -> str:
    built = build_summarizer_prompt(user_message="", context_docs="", web_results="")
    for msg in built.get("messages", []):
        if msg.get("role") == "system":
            base = str(msg.get("content", ""))
            break
    else:
        base = "You are a helpful assistant for deposition summarization."
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{base}\n\nToday is {today} (UTC)."


def _extract_text_from_event(event: Any) -> str | None:
    if event is None:
        return None
    if isinstance(event, str):
        return event

    for attr in ("text", "output_text", "content"):
        value = getattr(event, attr, None)
        if isinstance(value, str) and value.strip():
            return value

    content = getattr(event, "content", None)
    if content and hasattr(content, "parts"):
        parts = getattr(content, "parts", None) or []
        texts = [getattr(part, "text", "") for part in parts if getattr(part, "text", "")]
        merged = "\n".join(texts).strip()
        if merged:
            return merged

    return None


async def _run_once(
    *,
    conversation_id: str,
    thread_id: str,
    user_message: str,
    document_path: str | None,
    model_name: str | None,
) -> str:
    global _ADK_SESSION_SERVICE
    LlmAgent, Runner, InMemorySessionService, genai_types = _google_adk_imports()

    def rag_search(query: str) -> str:
        """Search uploaded deposition or local documents for relevant context."""
        return rag_tool(query, document_path=document_path)

    def web_search(query: str) -> str:
        """Search the web for relevant context."""
        return web_search_tool(query)

    model = model_name or os.getenv("GOOGLE_ADK_MODEL", "gemini-2.0-flash")
    if _ADK_SESSION_SERVICE is None:
        _ADK_SESSION_SERVICE = InMemorySessionService()

    runner = _ADK_RUNNERS.get(model)
    if runner is None:
        agent = LlmAgent(
            name="rev_assistant_google_adk",
            model=model,
            instruction=_instructions(),
            tools=[rag_search, web_search],
        )
        runner = Runner(
            app_name=_APP_NAME,
            agent=agent,
            session_service=_ADK_SESSION_SERVICE,
        )
        _ADK_RUNNERS[model] = runner

    user_id = conversation_id
    session_id = thread_id
    key = (user_id, session_id)
    if key not in _ADK_SESSIONS_CREATED and hasattr(_ADK_SESSION_SERVICE, "create_session"):
        maybe_coro = _ADK_SESSION_SERVICE.create_session(
            app_name=_APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        if asyncio.iscoroutine(maybe_coro):
            await maybe_coro
        _ADK_SESSIONS_CREATED.add(key)

    maybe_events = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=user_message)],
        ),
    )
    final_text = ""
    async for event in maybe_events:
        text = _extract_text_from_event(event)
        if text:
            final_text = text
    return final_text.strip() or "I could not produce a response."


def run_google_adk_agent(
    *,
    conversation_id: str,
    thread_id: str,
    user_message: str,
    document_path: str | None,
    model_name: str | None = None,
) -> AgentTurnResult:
    message = asyncio.run(
        _run_once(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_message=user_message,
            document_path=document_path,
            model_name=model_name,
        )
    )
    return AgentTurnResult(assistant_message=message, raw_state=None)
