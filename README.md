# Multi-Agent SDK + Braintrust Demo

This repo runs a single FastAPI + React chat app that keeps one Braintrust trace per `conversation_id` while letting you plug in three different agent runtimes. The multi-turn trace story lives in the backend, so the README now points directly at the code that wires the root span, per-turn spans, and the per-agent persistence logic.

## How one trace survives multiple turns
1. `src/backend/main.py:108-200` maintains a `SessionStore` row per `conversation_id`, storing the serialized root span export, `thread_id`, document attachment, and transcript. The handler then passes that export into `_handle_chat_turn`, which wraps `run_agent_turn` and logs both metadata and I/O so each `chat_turn` span is attached to the shared root.

```python
# src/backend/main.py lines 108-200
session = session_store.get_or_create_session(request.conversation_id)
root_span_export = session.root_span_export or None
root_span_id = session.root_span_id or None
created_root = False
thread_id = session.thread_id or str(uuid.uuid4())
if not root_span_export or not root_span_id:
    with logger.start_span(name="Rev Agent") as root_span:
        root_span.log(...)
        root_span_id = root_span.root_span_id
    root_span_export = root_span.export()
session_store.update_root_span(...)
...
turn, span_id, span_export = _handle_chat_turn(..., root_parent=root_span_export, ...)
```

2. `_handle_chat_turn` creates a `chat_turn` span (see `main.py:60-105`), inserts the same metadata/ids, and flushes updates back into the stored root span after each agent turn so Braintrust retains the full transcript:

```python
# src/backend/main.py lines 60-105
with logger.start_span(name="chat_turn", parent=root_parent) as span:
    turn = run_agent_turn(...)
    span.log(metadata={...})
    span.log(input={...}, output={...})
span_export = span.export()
return turn, span.span_id, span_export
```

3. `SessionStore` (`src/backend/storage/session_store.py:19-114`) keeps the shared `thread_id`, root span, transcript array, and uploaded document path per conversation so every request can rehydrate the same trace context.

```python
# src/backend/storage/session_store.py lines 55-114
conn.execute("SELECT ... FROM sessions WHERE conversation_id = ?", (conversation_id,))
...
session_store.update_transcript(conversation_id, output_messages)
```

## Per-agent multi-turn highlights
Each runtime sits behind `src/backend/agent/runner.py:14-62`, but the multi-turn behavior is implemented inside each agent.

### LangGraph (state graph handles the turns)
- Entry point: `run_langgraph_agent` calls `run_graph` with `conversation_id`, `thread_id`, and any attached document.
- `run_graph` builds a `StateGraph` (`src/backend/agent/graph.py:117-155`) that keeps `MessagesState` for the current conversation and reuses the same `RunnableConfig` so LangGraph callbacks stay attached to the `thread_id` spanning multiple tools.
- Tools (`rag_search`, `web_search`) are bound once per model, and document prompts are injected via `document_path` to keep turn continuity.

```python
# src/backend/agent/graph.py lines 117-155
messages: List[AnyMessage] = [HumanMessage(content=user_message)]
if document_path:
    messages.insert(0, SystemMessage(...))
initial_state = {"messages": messages, ...}
config = {"configurable": {"thread_id": thread_id}, ...}
return graph.invoke(initial_state, config=cast(Any, config))
```

### OpenAI Agents SDK (processor + Braintrust tracing)
- The agent registers `BraintrustTracingProcessor` so every run emits nested spans while remaining under the `chat_turn` span created in `main.py`.
- Tools (`rag_search`, `web_search`) share the document path and the common prompt built via `build_summarizer_prompt`.
- Instructions and metadata are identical turn-to-turn, and the run happens with the same `conversation_id`/`thread_id` from the FastAPI handler.

```python
# src/backend/agent/openai_agents_agent.py lines 65-105
_agent = Agent(..., instructions=_instructions(), tools=[rag_search, web_search], model=selected_model)
result = Runner.run_sync(agent, user_message)
return AgentTurnResult(assistant_message=str(message), raw_state={"result": str(result)})
```

### Google ADK (session-backed multi-turn)
- `run_google_adk_agent` caches a per-model runner and session service.
- Sessions are keyed on `(conversation_id, thread_id)` so each turn uses the same ADK session; the call to `Runner.run_async` uses `genai_types.Content` with the new user message.
- The handler streams events, extracts the latest assistant text, and returns it while the shared session ties back to the trace root.

```python
# src/backend/agent/google_adk_agent.py lines 37-120
if key not in _ADK_SESSIONS_CREATED:
    _ADK_SESSION_SERVICE.create_session(...)
maybe_events = runner.run_async(..., new_message=Content(...))
async for event in maybe_events:
    text = _extract_text_from_event(event)
return AgentTurnResult(assistant_message=message, raw_state=None)
```

## Supporting pieces
- `src/backend/agent/prompts.py:17-90` loads the `legal-deposition-assistant` Braintrust prompt for every runtime and logs metadata on the current span.
- `src/backend/agent/tools.py:10-42` wraps RAG and Tavily web search tools with Braintrust tracing so all runtimes share the same tool set.
- Feedback spans attach directly to `msg.span_id` via `/feedback` (`src/backend/main.py:200-232`), ensuring ratings map back to the same `chat_turn` span.

## Prerequisites
- Python 3.11+ (use `uv`)
- Node 18+
- Braintrust account + API key
- OpenAI API key (LangGraph and OpenAI Agents SDK examples)
- Tavily API key (web search tool)
- For Google ADK example: set `GOOGLE_API_KEY` (or Vertex `project`/`location` auth)

## Environment setup
1. Copy `.env.example` to `.env` and fill in values.
2. Set `AGENT_FRAMEWORK` to one of:
   - `langgraph`
   - `openai_agents`
   - `google_adk`
3. Export variables if you prefer shell env vars.

## Backend setup (uv)
1. Create a virtualenv and install deps:
   - `uv venv`
   - `source .venv/bin/activate`
   - `uv sync`
2. Optional framework extras:
   - `uv sync --extra openai-agents`
   - `uv sync --extra google-adk`
3. Run the API:
   - `uv run uvicorn src.backend.main:app --reload`
4. Health check:
   - `GET http://localhost:8000/health`
5. See active framework:
   - `GET http://localhost:8000/frameworks`

## Frontend setup
1. `cd src/frontend`
2. `npm install`
3. `npm run dev`
4. Open `http://localhost:5173`
5. UI is styled with Tailwind v4 and shadcn/ui primitives.

## Braintrust setup
1. Create a Braintrust project (name it `rev-langgraph-demo` or set `BRAINTRUST_PROJECT`).
2. Create the prompt with slug:
   - `legal-deposition-assistant`
3. Add environment versions if desired and set `BRAINTRUST_PROMPT_ENV` to `dev`, `staging`, or `production`.
4. Put your API key in `.env` as `BRAINTRUST_API_KEY=...`.

## API usage
`POST /chat`
- Body: `{ "conversation_id": "conv-123", "message": "..." }`
- Response includes `span_id` and `root_span_id` for trace continuity.

`POST /upload`
- Multipart form with `conversation_id` and `file`
- The file is stored and associated with the conversation.

`POST /feedback`
- Body: `{ "span_id": "span_123", "rating": "up" }`

## Notes
- RAG tests are skipped unless `OPENAI_API_KEY` is set.
- Feedback test is skipped unless `BRAINTRUST_API_KEY` is set.
- Prompts are loaded from Braintrust if available. Local fallbacks are used when prompts are missing or unavailable.

## References
- Braintrust LangGraph integration: https://www.braintrust.dev/docs/integrations/sdk-integrations/langgraph
- Braintrust LangChain integration: https://www.braintrust.dev/docs/integrations/langchain
- Braintrust OpenAI Agents integration: https://www.braintrust.dev/docs/integrations/sdk-integrations/openai-agents
- Braintrust Google ADK integration: https://www.braintrust.dev/docs/integrations/sdk-integrations/google-adk
- Braintrust feedback/labels: https://www.braintrust.dev/docs/annotate/labels

## Attribution
Portions of the frontend UI are adapted from Vercel's `ai-chatbot` repository under the Apache 2.0 license: https://github.com/vercel/ai-chatbot
