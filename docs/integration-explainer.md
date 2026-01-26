 # Integration Explainer

 This document explains how the demo satisfies the customer requirements:
 tracing, multi-turn span continuity, prompt management, tool usage (RAG + web),
 feedback logging, and a minimal UI.

 ## 1. LangGraph agent with tools
 **Where:** `src/backend/agent/graph.py`, `src/backend/agent/tools.py`, `src/backend/agent/rag.py`

 - The graph has explicit nodes for routing, retrieval, web search, and synthesis.
 - `rag_tool` uses a FAISS index built from `data/sample_deposition.txt`.
 - `web_search_tool` uses Tavily to fetch external context.

 Why this matches the requirement: it demonstrates tools (RAG + web) in a
 multi-actor LangGraph pipeline.

## 1b. Document uploads (optional)
**Where:** `src/backend/main.py`, `src/backend/storage/session_store.py`, `src/frontend/src/App.tsx`

- Users can upload a deposition or document via `/upload`.
- The backend stores the file under `data/uploads/` and associates it to the
  conversation.
- The RAG pipeline uses the uploaded document when present.

 ## 2. Braintrust prompt loading
 **Where:** `src/backend/agent/prompts.py`, `docs/prompt-registry.md`

 - Prompts are loaded with `load_prompt(project=..., slug=...)`.
 - If the prompt is missing, a fallback system prompt is used.
 - Prompt variables are passed in via `build_prompt`.

 Why this matches the requirement: prompts are stored and versioned in Braintrust
 but can still run locally with fallbacks.

 ## 3. Tracing LangGraph executions
 **Where:** `src/backend/agent/tracing.py`, `src/backend/main.py`

 - `BraintrustCallbackHandler` is set as the global LangChain handler.
 - LangGraph node execution and LLM calls are traced automatically.
 - Each `/chat` call is wrapped in a manual span `chat_turn` using `@traced`.

 Why this matches the requirement: it instruments LangGraph and adds app-level
 spans so the trace includes both graph execution and API-level boundaries.

 ## 4. Multi-turn trace continuity
 **Where:** `src/backend/storage/session_store.py`, `src/backend/main.py`

 - A conversation is keyed by `conversation_id`.
 - On the first turn, we store both `root_span_id` and `root_span_export`.
 - On later turns, we use `parent_context(root_span_export)` so new spans are
   attached to the original trace.

 Why this matches the requirement: every turn becomes a new span under the same
 root trace, even across multiple requests.

 ## 5. Feedback logging (thumbs up/down)
 **Where:** `src/backend/main.py`, `src/frontend/src/App.tsx`

 - The backend uses `logger.log_feedback(...)` with `scores` + `tags`.
 - The frontend stores the `span_id` per assistant message and posts feedback.

 Why this matches the requirement: feedback is attached to specific spans, not
 just the overall trace.

## 5b. Logging attachments to Braintrust
**Where:** `src/backend/main.py`

- The `/upload` endpoint logs the uploaded file using `Attachment`.
- This creates a trace entry with the uploaded document linked to the span.

Reference: https://www.braintrust.dev/docs/instrument/attachments

 ## 6. Simple web app for chat + feedback
 **Where:** `src/frontend/`

 - React UI maintains a stable `conversation_id` in `localStorage`.
 - Each assistant response carries `span_id` and can be rated.

 Why this matches the requirement: the UI shows multi-turn interactions and
 allows feedback per turn.

 ## 7. Git workflow strategy (P1)
 **Where:** `docs/braintrust-git-workflow.md`

 - Describes how prompt changes and environment promotions can be tracked
   via webhooks and mapped to git tags/releases.

 ## Notes and references
 - Braintrust LangGraph integration:
   https://www.braintrust.dev/docs/integrations/sdk-integrations/langgraph
 - Braintrust prompt + feedback docs:
   https://www.braintrust.dev/docs/annotate/labels
