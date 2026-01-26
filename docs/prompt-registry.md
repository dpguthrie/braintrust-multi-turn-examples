# Braintrust Prompt Registry

This demo expects two prompts to exist in Braintrust. If they do not, the app
falls back to a simple built-in prompt.

## legal-deposition-assistant

**Purpose:** Provide system-level guidance for the tool-calling agent.

**Variables:**
- `user_message` (string): The user's message.
- `context_docs` (string): Retrieved document context (RAG).
- `web_results` (string): Web search results.

**Expected behavior:** Encourage use of `rag_search` for document questions and
`web_search` for external facts, cite the source (docs or web), and keep it concise.

**Environments:** Prompts can be loaded by environment by setting
`BRAINTRUST_PROMPT_ENV` (e.g. `dev`, `staging`, `production`).
