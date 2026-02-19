# Rev Multi-Agent SDK + Braintrust Demo

This repo contains one shared chat app with three interchangeable agent runtimes:
- LangGraph
- OpenAI Agents SDK
- Google ADK

All three use the same:
- FastAPI chat API and React UI
- RAG + web-search tools
- Braintrust prompt loading
- Braintrust tracing model: one root trace per conversation, child span per turn

## What it demonstrates
- SDK-swappable multi-turn chat architecture
- Consistent trace continuity across frameworks
- Feedback logging (thumbs up/down) per assistant turn

## Repo layout
- `src/backend/` FastAPI app
- `src/backend/agent/` framework adapters and shared tools/prompts
- `src/backend/agent/graph.py` LangGraph implementation
- `src/backend/agent/openai_agents_agent.py` OpenAI Agents SDK implementation
- `src/backend/agent/google_adk_agent.py` Google ADK implementation
- `src/backend/storage/` session store (SQLite)
- `src/frontend/` React UI (Vite)
- `data/` sample deposition text
- `docs/` workflow and explainer docs

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
3. Add environment versions if desired and set `BRAINTRUST_PROMPT_ENV` to
   `dev`, `staging`, or `production`.
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

## Trace continuity note
- For multi-turn chats, this app stores a per-conversation root span export in SQLite.
- Each turn span is created with that root as the parent.
- Both root span and turn spans include `agent_framework` metadata to support filtering in Braintrust UI.
- In the Google ADK adapter, ADK sessions are keyed by `conversation_id` + `thread_id` so ADK memory/session continuity aligns with the same trace root.
- This is the key pattern for keeping one trace per session across all frameworks.
- If you use `adk run <agent_name>` directly from CLI for each turn, separate traces are expected unless you add your own persisted parent-trace context.

## OpenAI Agents multi-turn
- Set `AGENT_FRAMEWORK=openai_agents`.
- Keep the same `conversation_id` across turns when calling `POST /chat`.
- The backend persists one root span per conversation and creates one `chat_turn` child span per request.
- OpenAI Agents internal events are captured by the Braintrust OpenAI trace processor (`BraintrustTracingProcessor`) in the adapter, so traces are not limited to a flat top-level span.
- Use `agent_framework=openai_agents` in Braintrust metadata filters to isolate these sessions.

Example:
```bash
curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-openai-1","message":"Summarize key facts in one sentence."}'

curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-openai-1","message":"Now give me two follow-up questions."}'
```

Expected behavior:
- Same `root_span_id` in both responses.
- Different `span_id` per turn.
- Nested OpenAI Agents spans visible under the turn/root trace tree in Braintrust.

## LangGraph multi-turn
- Set `AGENT_FRAMEWORK=langgraph`.
- Keep the same `conversation_id` across turns when calling `POST /chat`.
- LangGraph internals are traced through the Braintrust LangChain callback handler, so model/tool nodes appear as nested spans.
- Use `agent_framework=langgraph` in Braintrust metadata filters.

Example:
```bash
curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-langgraph-1","message":"Summarize key facts in one sentence."}'

curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-langgraph-1","message":"Now give me two follow-up questions."}'
```

Expected behavior:
- Same `root_span_id` in both responses.
- Different `span_id` per turn.
- Nested LangGraph spans (for example model/tool call nodes) under each `chat_turn`.

## Google ADK multi-turn
- Set `AGENT_FRAMEWORK=google_adk`.
- Provide Gemini/Google credentials:
  - `GOOGLE_API_KEY=...` (preferred), or
  - `GEMINI_API_KEY=...`, or
  - Vertex AI auth (`vertexai`, `project`, `location`).
- Keep the same `conversation_id` across turns when calling `POST /chat`.
- The adapter maps ADK session identity to `conversation_id` + `thread_id`, so ADK memory/session continuity follows the same Braintrust root trace.
- Use `agent_framework=google_adk` in Braintrust metadata filters.

Example:
```bash
curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-adk-1","message":"Summarize key facts in one sentence."}'

curl -s localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id":"demo-adk-1","message":"Now give me two follow-up questions."}'
```

Expected behavior:
- Same `root_span_id` in both responses.
- Different `span_id` per turn.
- ADK execution spans nested under the same session trace.

Common ADK issue:
- `RESOURCE_EXHAUSTED (429)` indicates API quota/billing limits on the configured Gemini project/key, not a tracing/session wiring bug.

## Notes
- RAG tests are skipped unless `OPENAI_API_KEY` is set.
- Feedback test is skipped unless `BRAINTRUST_API_KEY` is set.
- Prompts are loaded from Braintrust if available. Local fallbacks are used when prompts are missing or unavailable.

## References
- Braintrust LangGraph integration:
  https://www.braintrust.dev/docs/integrations/sdk-integrations/langgraph
- Braintrust LangChain integration:
  https://www.braintrust.dev/docs/integrations/langchain
- Braintrust OpenAI Agents integration:
  https://www.braintrust.dev/docs/integrations/sdk-integrations/openai-agents
- Braintrust Google ADK integration:
  https://www.braintrust.dev/docs/integrations/sdk-integrations/google-adk
- Braintrust feedback/labels:
  https://www.braintrust.dev/docs/annotate/labels

## Attribution
Portions of the frontend UI are adapted from Vercel's `ai-chatbot` repository
under the Apache 2.0 license: https://github.com/vercel/ai-chatbot
