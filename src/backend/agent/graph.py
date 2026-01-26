from __future__ import annotations

import operator
import os
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, List, TypedDict, cast
from typing_extensions import Annotated

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph

from src.backend.agent.prompts import build_summarizer_prompt
from src.backend.agent.tools import rag_tool, web_search_tool


class MessagesState(TypedDict):
    messages: Annotated[List[AnyMessage], operator.add]
    llm_calls: int
    document_path: str | None


def _model(model_name: str | None = None):
    selected = model_name or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    return init_chat_model(selected, temperature=0)


@tool("rag_search")
def rag_search(query: str, document_path: str | None = None) -> str:
    """Search uploaded deposition or local documents for relevant context."""
    return rag_tool(query, document_path=document_path)


@tool("web_search")
def web_search(query: str) -> str:
    """Search the web for relevant context."""
    return web_search_tool(query)


TOOLS = [rag_search, web_search]
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def system_prompt() -> str:
    built = build_summarizer_prompt(
        user_message="",
        context_docs="",
        web_results="",
    )
    for msg in built.get("messages", []):
        if msg.get("role") == "system":
            base = str(msg.get("content", ""))
            break
    else:
        base = "You are a helpful assistant for deposition summarization."
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{base}\n\nToday is {today} (UTC)."


def llm_call(state: MessagesState, config: RunnableConfig | None = None) -> dict:
    model_name = None
    if config:
        model_name = (config.get("metadata") or {}).get("model_name")
    model = _model(model_name).bind_tools(TOOLS)
    response = model.invoke(
        [SystemMessage(content=system_prompt())] + state["messages"]
    )
    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def tool_node(state: MessagesState) -> dict:
    result_messages: List[ToolMessage] = []
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    for tool_call in tool_calls:
        name = tool_call.get("name")
        args = tool_call.get("args", {}) or {}
        if name == "rag_search":
            args = {**args, "document_path": state.get("document_path")}
        tool_fn = TOOLS_BY_NAME.get(name)
        if tool_fn is None:
            output = f"Unknown tool: {name}"
        else:
            output = tool_fn.invoke(args)
        result_messages.append(
            ToolMessage(content=str(output), tool_call_id=tool_call.get("id"))
        )
    return {"messages": result_messages}


def should_continue(state: MessagesState) -> str:
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    if tool_calls:
        return "tool_node"
    return END


@lru_cache(maxsize=1)
def get_graph():
    builder = StateGraph(MessagesState)
    builder.add_node("llm_call", llm_call)
    builder.add_node("tool_node", tool_node)

    builder.add_edge(START, "llm_call")
    builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    builder.add_edge("tool_node", "llm_call")
    return builder.compile()


def run_graph(
    conversation_id: str,
    thread_id: str,
    user_message: str,
    document_path: str | None,
    model_name: str | None = None,
    callbacks=None,
    metadata: dict | None = None,
) -> dict:
    graph = get_graph()
    messages: List[AnyMessage] = [HumanMessage(content=user_message)]
    if document_path:
        filename = os.path.basename(document_path)
        messages.insert(
            0,
            SystemMessage(
                content=(
                    "A document is available for this conversation. "
                    "Use the rag_search tool to answer questions about it. "
                    f"Document filename: {filename}."
                )
            ),
        )
    initial_state: MessagesState = {
        "messages": messages,
        "llm_calls": 0,
        "document_path": document_path,
    }
    config = {
        "configurable": {"thread_id": thread_id},
    }
    if callbacks:
        config["callbacks"] = callbacks
    if metadata:
        config["metadata"] = metadata
    if model_name:
        config.setdefault("metadata", {})
        config["metadata"]["model_name"] = model_name
    return graph.invoke(initial_state, config=cast(Any, config))
