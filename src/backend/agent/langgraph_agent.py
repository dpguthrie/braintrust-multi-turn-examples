from __future__ import annotations

from typing import Any

from src.backend.agent.graph import run_graph


def run_langgraph_agent(
    *,
    conversation_id: str,
    thread_id: str,
    user_message: str,
    document_path: str | None,
    model_name: str | None = None,
    callbacks: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return run_graph(
        conversation_id=conversation_id,
        thread_id=thread_id,
        user_message=user_message,
        document_path=document_path,
        model_name=model_name,
        callbacks=callbacks,
        metadata=metadata,
    )
