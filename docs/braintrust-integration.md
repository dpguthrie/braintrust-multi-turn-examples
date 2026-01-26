## Braintrust Integration Guide

This document explains how the demo integrates Braintrust across tracing,
prompts, tools, feedback, and multi-turn chat.

### Agent tracing setup

- **Initialization**: The Braintrust logger is initialized once per app
  startup in `src/backend/agent/tracing.py` via `init_tracing()`. It reads
  `BRAINTRUST_API_KEY` and `BRAINTRUST_PROJECT` and sets a global
  `BraintrustCallbackHandler` for LangChain/LangGraph callbacks.
- **Per-request handler**: Each chat request builds a new
  `BraintrustCallbackHandler` via `build_callback_handler(logger)` and passes
  it to the LangGraph invoke call, so each LLM/tool invocation is traced.
- **Span structure**: The API creates a top-level span named `Rev Agent`
  and nests each chat turn as a child span (`chat_turn`) using the exported
  parent from the root span.

Relevant files:
- `src/backend/agent/tracing.py`
- `src/backend/main.py`
- `src/backend/agent/graph.py`

### Prompts pulled from Braintrust

- **Prompt loading**: Prompts are loaded from Braintrust using
  `load_prompt(project=..., slug=..., environment=...)` in
  `src/backend/agent/prompts.py`.
- **Prompt usage**: The system prompt is derived from the Braintrust prompt
  messages in `src/backend/agent/graph.py` (`system_prompt()`), then appended
  with the current date.
- **Prompt variables**: The app passes
  `user_message`, `context_docs`, `web_results` to `prompt.build(...)`. It also
  includes an `input` object so prompt templates can use either
  `{{user_message}}` or `{{input.user_message}}`.
- **Version logging**: When a Braintrust prompt is loaded, the code logs
  prompt metadata (slug, id, version, environment, source) into the active span.
  If loading fails, it logs `source=fallback`.

Relevant files:
- `src/backend/agent/prompts.py`
- `src/backend/agent/graph.py`
- `docs/prompt-registry.md`

### Custom tool definitions

- **Tool registration**: Tools are defined in `src/backend/agent/graph.py` using
  `@tool` decorators and bound to the model with `bind_tools`.
  - `rag_search`: document retrieval
  - `web_search`: external search
- **Braintrust tracing**: Tool implementations are wrapped with
  `@traced(...)` in `src/backend/agent/tools.py`, so each tool call appears
  as its own span in Braintrust.
- **Attachment logging**: When `rag_search` runs with a document attached,
  the tool logs the document as a Braintrust `Attachment` to the active span.

Relevant files:
- `src/backend/agent/graph.py`
- `src/backend/agent/tools.py`
- `src/backend/agent/rag.py`

### Feedback capture

- **API endpoint**: The frontend submits feedback to `/feedback` with the
  `span_id` of the assistant turn and optional rating/comment.
- **Braintrust logging**: The backend uses `logger.log_feedback(...)` to attach
  feedback to the exact span that produced the response.
- **Comment-only**: The API accepts feedback with no rating (comment-only).

Relevant files:
- `src/backend/main.py`
- `src/backend/api/models.py`
- `src/frontend/src/api.ts`

### Chat / thread tracing (multi-turn)

- **Session storage**: A SQLite session store persists
  `conversation_id`, `thread_id`, `root_span_id`, `root_span_export`, and
  transcript data per conversation.
- **Root span**: The first message creates a `Rev Agent` root span and saves
  its exported parent (`root_span_export`) in the session.
- **Child spans**: Each subsequent turn creates a `chat_turn` span using the
  stored `root_span_export` as the parent, keeping all turns in a single trace.
- **Root span updates**: After each turn, `update_span(...)` writes the running
  conversation transcript to the root span’s input/output.

Relevant files:
- `src/backend/main.py`
- `src/backend/storage/session_store.py`

### Environment and prompt versions

- **Environment selection**: Set `BRAINTRUST_PROMPT_ENV` to load prompts from a
  specific environment (e.g. `dev`, `staging`, `production`).
- **Version promotion**: Manage prompt versions in Braintrust and promote
  them between environments without code changes.

Related docs:
- https://www.braintrust.dev/docs/deploy/environments
- https://www.braintrust.dev/docs/deploy/prompts#use-environments

### How to explain this in a demo

1. Show a chat request and the resulting trace tree in Braintrust:
   `Rev Agent` root span → `chat_turn` → tool/LLM spans.
2. Highlight prompt metadata on a span (slug, version, environment).
3. Trigger `rag_search` and show the document attachment logged on the tool span.
4. Submit feedback and show it attached to the response span.
5. Send multiple turns and show them in the same trace via `root_span_id`.
