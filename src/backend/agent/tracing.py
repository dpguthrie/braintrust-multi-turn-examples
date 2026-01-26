import os
from contextlib import contextmanager
from typing import Generator

from braintrust import current_span, init_logger, parent_context, traced
from braintrust_langchain import BraintrustCallbackHandler, set_global_handler
from dotenv import load_dotenv

_logger = None


def init_tracing():
    global _logger
    if _logger is not None:
        return _logger
    load_dotenv()
    project = os.getenv("BRAINTRUST_PROJECT", "rev-langgraph-demo")
    api_key = os.getenv("BRAINTRUST_API_KEY")
    if not api_key:
        raise RuntimeError(
            "BRAINTRUST_API_KEY is not set. Check your .env or environment."
        )
    _logger = init_logger(project=project, api_key=api_key)
    handler = BraintrustCallbackHandler(logger=_logger)
    set_global_handler(handler)
    return _logger


def build_callback_handler(logger):
    return BraintrustCallbackHandler(logger=logger)


def get_current_span():
    return current_span()


@contextmanager
def span_parent_context(parent_export: str | None) -> Generator[None, None, None]:
    if parent_export:
        with parent_context(parent_export):
            yield
    else:
        yield


@traced(name="chat_turn")
def traced_chat_turn(func, *args, **kwargs):
    return func(*args, **kwargs)
