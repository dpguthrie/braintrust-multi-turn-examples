# Braintrust Prompt + Git Workflow (P1)

This demo assumes prompts live in Braintrust and are pulled into the app at runtime
via `load_prompt`. The source of truth for prompt text is Braintrust, and git stores
only the prompt identifiers and expected variables.

## Suggested Workflow

1. **Edit prompts in Braintrust**
   - Update the prompt in the Braintrust UI or via API.
   - Use environments (e.g., `dev`, `staging`, `prod`) to control promotion.

2. **Promote to an environment**
   - After validation, promote the prompt version to the target environment.
   - This produces a stable reference for the backend to load.

3. **Webhook to trigger repo updates**
   - Configure Braintrust environment webhooks to call a small service or CI job.
   - That job updates:
     - `docs/prompt-registry.md` with the current prompt version metadata
     - Optional `CHANGELOG.md` for prompt revisions

4. **Git tagging and release alignment**
   - When prompts are promoted to `prod`, create a git tag or release that records:
     - Prompt environment version
     - App commit SHA
     - Relevant evaluation results

5. **Trace-level metadata**
   - Include prompt metadata in spans (prompt slug, version, environment) so traces
     can be filtered by prompt version in Braintrust.

## Why this matters

- Keeps prompt changes auditable while still using Braintrust as the source of truth.
- Avoids drift between code and prompt environments.
- Enables rollbacks by re-promoting a previous prompt version.
