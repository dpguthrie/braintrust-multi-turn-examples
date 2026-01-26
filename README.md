 # Rev LangGraph + Braintrust Demo

 This repo contains a minimal LangGraph agent wired to Braintrust for tracing,
 prompt management, and feedback logging. It also includes a simple React UI
 for multi-turn chat and per-turn thumbs up/down feedback.

 ## What it demonstrates
 - LangGraph agent with RAG + web search tools
 - Braintrust tracing with multi-turn continuation
 - Prompt loading from Braintrust using `load_prompt`
 - Feedback logging (thumbs up/down) per assistant turn
 - Simple React UI for chat and feedback

 ## Repo layout
 - `src/backend/` FastAPI app + LangGraph agent
 - `src/backend/agent/` graph, tools, prompts, tracing
 - `src/backend/storage/` session store (SQLite)
 - `src/frontend/` React UI (Vite)
 - `data/` sample deposition text
 - `docs/` workflow and explainer docs

## Prerequisites
- Python 3.11+ (use `uv`)
 - Node 18+
 - Braintrust account + API key
 - OpenAI API key
 - Tavily API key (for web search tool)

 ## Environment setup
 1. Copy `.env.example` to `.env` and fill in values.
 2. Export the variables if you prefer shell env vars.

## Backend setup (uv)
1. Create a virtualenv and install deps:
   - `uv venv`
   - `source .venv/bin/activate`
   - `uv sync`
2. Run the API:
   - `uv run uvicorn src.backend.main:app --reload`
3. Health check:
   - `GET http://localhost:8000/health`

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
 - `POST /chat`
   - Body: `{ "conversation_id": "conv-123", "message": "..." }`
   - Response includes `span_id` and `root_span_id` for trace continuity.
- `POST /upload`
  - Multipart form with `conversation_id` and `file`
  - The file is stored and associated with the conversation.
 - `POST /feedback`
   - Body: `{ "span_id": "span_123", "rating": "up" }`

 ## Notes
 - RAG tests are skipped unless `OPENAI_API_KEY` is set.
 - Feedback test is skipped unless `BRAINTRUST_API_KEY` is set.
 - Prompts are loaded from Braintrust if available. Local fallbacks are used
   when prompts are missing or unavailable.

 ## References
 - Braintrust LangGraph integration:
   https://www.braintrust.dev/docs/integrations/sdk-integrations/langgraph
 - Braintrust LangChain integration:
   https://www.braintrust.dev/docs/integrations/langchain
 - Braintrust feedback/labels:
   https://www.braintrust.dev/docs/annotate/labels

## Attribution
Portions of the frontend UI are adapted from Vercel's `ai-chatbot` repository
under the Apache 2.0 license: https://github.com/vercel/ai-chatbot
