import os

import pytest

from src.backend.agent.rag import retrieve_context


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
def test_rag_returns_context():
    context = retrieve_context("Where was Jane Doe on March 12?")
    assert "North Market Cafe" in context
