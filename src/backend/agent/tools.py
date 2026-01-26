import os
from typing import List

from braintrust import Attachment, current_span, traced
from tavily import TavilyClient

from src.backend.agent.rag import retrieve_context


@traced(name="rag_retrieve")
def rag_tool(query: str, k: int = 3, document_path: str | None = None) -> str:
    if document_path:
        span = current_span()
        try:
            attachment = Attachment(
                data=document_path,
                filename=os.path.basename(document_path),
                content_type="application/pdf" if document_path.lower().endswith(".pdf") else "text/plain",
            )
            span.log(
                metadata={"rag_document_path": document_path},
                input={"document": attachment},
            )
        except Exception:
            # Avoid failing tool execution if attachment logging fails.
            span.log(metadata={"rag_document_path": document_path})
    return retrieve_context(query, k=k, path=document_path)


@traced(name="web_search")
def web_search_tool(query: str, max_results: int = 3) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    client = TavilyClient(api_key=api_key)
    results = client.search(query, max_results=max_results)
    items: List[str] = []
    for item in results.get("results", []):
        title = item.get("title", "Untitled")
        url = item.get("url", "")
        content = item.get("content", "")
        items.append(f"- {title} ({url}): {content}")
    return "\n".join(items)
