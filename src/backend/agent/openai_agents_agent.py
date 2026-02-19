from __future__ import annotations

import os
from datetime import datetime, timezone

from src.backend.agent.prompts import build_summarizer_prompt
from src.backend.agent.tools import rag_tool, web_search_tool
from src.backend.agent.types import AgentTurnResult

_BT_TRACE_PROCESSOR_CONFIGURED = False


def _openai_agents_imports():
    try:
        from agents import Agent, Runner, add_trace_processor, function_tool
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI Agents SDK is not installed. Install with: uv sync --extra openai-agents"
        ) from exc
    return Agent, Runner, add_trace_processor, function_tool


def _ensure_braintrust_processor(add_trace_processor) -> None:
    global _BT_TRACE_PROCESSOR_CONFIGURED
    if _BT_TRACE_PROCESSOR_CONFIGURED:
        return
    try:
        from braintrust.wrappers.openai import BraintrustTracingProcessor
    except ImportError as exc:
        raise RuntimeError(
            "Braintrust OpenAI Agents trace processor unavailable. Upgrade braintrust package."
        ) from exc
    add_trace_processor(BraintrustTracingProcessor())
    _BT_TRACE_PROCESSOR_CONFIGURED = True


def _instructions() -> str:
    built = build_summarizer_prompt(user_message="", context_docs="", web_results="")
    for msg in built.get("messages", []):
        if msg.get("role") == "system":
            base = str(msg.get("content", ""))
            break
    else:
        base = "You are a helpful assistant for deposition summarization."
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{base}\n\nToday is {today} (UTC)."


def run_openai_agents_agent(
    *,
    conversation_id: str,
    thread_id: str,
    user_message: str,
    document_path: str | None,
    model_name: str | None = None,
) -> AgentTurnResult:
    _ = (conversation_id, thread_id)
    Agent, Runner, add_trace_processor, function_tool = _openai_agents_imports()
    _ensure_braintrust_processor(add_trace_processor)

    @function_tool
    def rag_search(query: str) -> str:
        """Search uploaded deposition or local documents for relevant context."""
        return rag_tool(query, document_path=document_path)

    @function_tool
    def web_search(query: str) -> str:
        """Search the web for relevant context."""
        return web_search_tool(query)

    selected_model = model_name or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    agent = Agent(
        name="rev_assistant_openai_agents",
        instructions=_instructions(),
        tools=[rag_search, web_search],
        model=selected_model,
    )
    result = Runner.run_sync(agent, user_message)

    message = None
    if hasattr(result, "final_output"):
        message = result.final_output
    elif hasattr(result, "output_text"):
        message = result.output_text
    else:
        message = str(result)
    return AgentTurnResult(assistant_message=str(message), raw_state={"result": str(result)})
