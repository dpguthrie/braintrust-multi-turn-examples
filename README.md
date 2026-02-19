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
All three frameworks are dispatched through `src/backend/agent/runner.py`, and they all share the same root-span-persistence pattern from `main.py` described above. The differences are in how each framework handles **conversation memory** and how its internal spans get bridged into Braintrust.

### LangGraph (state graph + callback threading)

**How it works:** LangGraph has its own persistence mechanism via `thread_id` in the config, and LangChain's callback system propagates Braintrust spans automatically through `RunnableConfig`.

**Agent-side** (`src/backend/agent/graph.py:117-155`): Each turn invokes the compiled `StateGraph` with the same `thread_id`. The `BraintrustCallbackHandler` is passed via `config["callbacks"]`, so every LLM call and tool invocation inside the graph emits child spans automatically:

```python
# src/backend/agent/graph.py
config = {
    "configurable": {"thread_id": thread_id},
    "callbacks": callbacks,  # BraintrustCallbackHandler
    "metadata": metadata,
}
return graph.invoke(initial_state, config=cast(Any, config))
```

**Trace-side** (`src/backend/main.py`): The same `root_span_export` pattern applies — `main.py` creates a root span on the first turn, persists it, and parents every `chat_turn` span to it. The LangChain callback handler then nests LLM/tool spans inside that `chat_turn`.

### OpenAI Agents SDK (tracing processor)

**How it works:** The OpenAI Agents SDK has its own tracing system. Braintrust provides a `BraintrustTracingProcessor` that bridges agent-internal spans into the Braintrust trace tree.

**Agent-side** (`src/backend/agent/openai_agents_agent.py:23-34`): A `BraintrustTracingProcessor` is registered once at startup via `add_trace_processor`. After that, every `Runner.run_sync` call automatically emits nested spans (LLM calls, tool use) into whatever Braintrust span is active:

```python
# src/backend/agent/openai_agents_agent.py
from braintrust.wrappers.openai import BraintrustTracingProcessor
add_trace_processor(BraintrustTracingProcessor())

# Each turn is stateless — just pass the new message
result = Runner.run_sync(agent, user_message)
```

**Trace-side** (`src/backend/main.py`): Same pattern as the other frameworks — `main.py` creates and persists a root span, then parents each `chat_turn` to it. The tracing processor nests the agent's internal spans inside that `chat_turn`.

**Note:** Unlike LangGraph and ADK, the OpenAI Agents SDK doesn't manage conversation memory for you. The multi-turn transcript is maintained entirely by `main.py` and `SessionStore` — the agent itself sees only the current user message per turn.

### Google ADK (session-backed multi-turn)

**The problem:** When you use `adk run <agent_name>`, each invocation creates a separate Braintrust trace. For chat-style ADK agents that manage their own memory via `SessionService`, there's no built-in way to keep all turns under one trace.

**The solution:** Don't rely on `adk run` for tracing. Wrap ADK calls in your own service layer and manage the Braintrust root span yourself. Two things are happening in parallel — ADK session management (conversation memory) and Braintrust span management (trace continuity) — and they are independent of each other.

**ADK session continuity** (`src/backend/agent/google_adk_agent.py:85-129`): An `InMemorySessionService` is created once and shared across turns. Sessions are keyed on `(conversation_id, thread_id)` so each turn reuses the same ADK session and conversation memory:

```python
# src/backend/agent/google_adk_agent.py
user_id = conversation_id
session_id = thread_id
key = (user_id, session_id)
if key not in _ADK_SESSIONS_CREATED:
    _ADK_SESSION_SERVICE.create_session(
        app_name=_APP_NAME, user_id=user_id, session_id=session_id,
    )
    _ADK_SESSIONS_CREATED.add(key)

# Every subsequent turn just calls run_async with the same session
async for event in runner.run_async(
    user_id=user_id, session_id=session_id, new_message=...
):
    ...
```

**Braintrust trace continuity** (`src/backend/main.py:121-184`): This is the same pattern used by all three frameworks — on the first turn, create a root span and persist `span.export()`. On every turn, pass `parent=root_span_export` when starting a child span. After each turn, update the root span with the running transcript:

```python
# src/backend/main.py — first turn: create + persist root span
with logger.start_span(name="Rev Agent") as root_span:
    root_span_id = root_span.root_span_id
root_span_export = root_span.export()
session_store.update_root_span(conversation_id, root_span_id, root_span_export)

# Every turn: parent child spans to the root
with logger.start_span(name="chat_turn", parent=root_span_export) as span:
    turn = run_agent_turn(...)  # calls the ADK runner

# After each turn: update root span with full transcript
update_span(root_span_export, input={"messages": all_input}, output={"messages": all_output})
```

**Key takeaway:** `span.export()` serializes the span context into a string you can store anywhere (DB, Redis, etc.) and pass back as `parent=` on future turns. This is the mechanism that stitches separate ADK calls into a single trace — ADK's `SessionService` handles conversation memory, Braintrust's `span.export()`/`parent=` handles trace continuity.

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
