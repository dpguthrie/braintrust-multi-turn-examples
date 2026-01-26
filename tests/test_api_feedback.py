import os

import pytest
from fastapi.testclient import TestClient

from src.backend.main import app


@pytest.mark.skipif(
    not os.getenv("BRAINTRUST_API_KEY"),
    reason="BRAINTRUST_API_KEY not set",
)
def test_feedback_endpoint_accepts_payload():
    client = TestClient(app)
    response = client.post(
        "/feedback",
        json={"span_id": "span_123", "rating": "up", "comment": "Looks good"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
