import logging
import os
from typing import Any, Dict

from braintrust import current_span, load_prompt

SUMMARIZER_FALLBACK = (
    "You are a legal assistant helping summarize deposition testimony.\n"
    "Use tools when needed: rag_search for documents and web_search for external facts.\n"
    "Answer clearly, cite which source you used (doc or web), and be concise."
)


def _load_prompt(slug: str):
    project = os.getenv("BRAINTRUST_PROJECT")
    environment = os.getenv("BRAINTRUST_PROMPT_ENV")
    return load_prompt(project=project, slug=slug, environment=environment)


def _log_prompt_metadata(
    *,
    slug: str,
    source: str,
    prompt_id: str | None = None,
    version: str | None = None,
) -> None:
    span = current_span()
    span.log(
        metadata={
            "prompt": {
                "slug": slug,
                "id": prompt_id,
                "version": version,
                "environment": os.getenv("BRAINTRUST_PROMPT_ENV"),
                "source": source,
            }
        }
    )


def build_prompt(slug: str, variables: Dict[str, Any] | None = None) -> Dict[str, Any]:
    variables = variables or {}
    build_vars = {**variables, "input": variables}
    try:
        prompt = _load_prompt(slug)
        built = dict(prompt.build(**build_vars))
        logging.getLogger(__name__).info(
            "Loaded Braintrust prompt slug=%s env=%s",
            slug,
            os.getenv("BRAINTRUST_PROMPT_ENV"),
        )
        _log_prompt_metadata(
            slug=slug,
            source="braintrust",
            prompt_id=getattr(prompt, "id", None),
            version=getattr(prompt, "version", None),
        )
        return built
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Falling back to local prompt slug=%s env=%s error=%s",
            slug,
            os.getenv("BRAINTRUST_PROMPT_ENV"),
            exc,
        )
        _log_prompt_metadata(slug=slug, source="fallback")
        return {
            "messages": [
                {"role": "system", "content": SUMMARIZER_FALLBACK},
            ]
        }


def build_summarizer_prompt(
    user_message: str,
    context_docs: str,
    web_results: str,
) -> Dict[str, Any]:
    return build_prompt(
        "legal-deposition-assistant",
        {
            "user_message": user_message,
            "context_docs": context_docs,
            "web_results": web_results,
        },
    )


if __name__ == "__main__":
    print(build_summarizer_prompt("", "", "")["messages"][0]["content"])
