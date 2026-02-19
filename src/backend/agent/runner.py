from __future__ import annotations

import os
from typing import Any, Literal

from src.backend.agent.google_adk_agent import run_google_adk_agent
from src.backend.agent.langgraph_agent import run_langgraph_agent
from src.backend.agent.openai_agents_agent import run_openai_agents_agent
from src.backend.agent.types import AgentTurnResult

AgentFramework = Literal["langgraph", "openai_agents", "google_adk"]


def resolve_agent_framework() -> AgentFramework:
    selected = os.getenv("AGENT_FRAMEWORK", "langgraph").strip().lower()
    if selected not in {"langgraph", "openai_agents", "google_adk"}:
        raise ValueError(
            "AGENT_FRAMEWORK must be one of: langgraph, openai_agents, google_adk"
        )
    return selected  # type: ignore[return-value]


def run_agent_turn(
    *,
    framework: AgentFramework,
    conversation_id: str,
    thread_id: str,
    user_message: str,
    document_path: str | None,
    model_name: str | None = None,
    callbacks: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AgentTurnResult:
    if framework == "langgraph":
        state = run_langgraph_agent(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_message=user_message,
            document_path=document_path,
            model_name=model_name,
            callbacks=callbacks,
            metadata=metadata,
        )
        last = state["messages"][-1]
        return AgentTurnResult(assistant_message=getattr(last, "content", str(last)), raw_state=state)

    if framework == "openai_agents":
        return run_openai_agents_agent(
            conversation_id=conversation_id,
            thread_id=thread_id,
            user_message=user_message,
            document_path=document_path,
            model_name=model_name,
        )

    return run_google_adk_agent(
        conversation_id=conversation_id,
        thread_id=thread_id,
        user_message=user_message,
        document_path=document_path,
        model_name=model_name,
    )
