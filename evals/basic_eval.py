import os
import sys
import uuid
from pathlib import Path

from autoevals import Factuality
from braintrust import Eval
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

load_dotenv()

from src.backend.agent.graph import run_graph  # noqa: E402

DATA_PATH = os.getenv("DEPOSITION_SAMPLE_PATH", "./data/sample_deposition.txt")


def run_agent(question: str, document_path: str | None) -> str:
    conversation_id = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())
    state = run_graph(
        conversation_id=conversation_id,
        thread_id=thread_id,
        user_message=question,
        document_path=document_path,
    )
    return state["messages"][-1].content


def main() -> None:
    cases = [
        {
            "input": {
                "question": "Summarize the key events described in the deposition.",
                "document_path": DATA_PATH,
            },
            "expected": "The witness describes a car accident, the timing of events, and the injuries reported.",
        },
        {
            "input": {
                "question": "Who is the witness and what role do they describe?",
                "document_path": DATA_PATH,
            },
            "expected": "The witness is a participant in the incident and describes their observations.",
        },
    ]

    Eval(
        "rev-langgraph-demo",
        data=cases,
        task=lambda case: run_agent(case["question"], case["document_path"]),
        scores=[Factuality],
        metadata={
            "model": os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini"),
            "dataset": "basic_deposition_eval",
        },
    )


if __name__ == "__main__":
    main()
