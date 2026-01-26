import os
from pathlib import Path

from braintrust import Attachment, init_dataset
from dotenv import load_dotenv

load_dotenv()

PDF_PATH = os.path.expanduser("~/Downloads/deposition.pdf")
DATASET_NAME = os.getenv("BRAINTRUST_DATASET_NAME", "legal-deposition-questions")
PROJECT = os.getenv("BRAINTRUST_PROJECT", "rev-langgraph-demo")


def build_questions() -> list[str]:
    return [
        "Who is the witness, and what is their role or relationship to the parties?",
        "Walk me through the timeline of events in exact order, including dates and times.",
        "Where does the witness describe gaps or uncertainty about what they observed?",
        "Which documents did the witness review or rely on, and who provided them?",
        "Did the witness identify any prior statements that conflict with this testimony?",
        "What did the witness say about preparation for the deposition?",
        "What concrete damages or impacts were described (work, medical, daily life)?",
        "What additional people, locations, or records should be investigated next?",
    ]


def main() -> None:
    pdf = Path(PDF_PATH)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found at {pdf}")

    dataset = init_dataset(project=PROJECT, name=DATASET_NAME)
    attachment = Attachment(
        data=str(pdf),
        filename=pdf.name,
        content_type="application/pdf",
    )

    for question in build_questions():
        dataset.insert(
            input={
                "question": question,
                "document": attachment,
            },
            metadata={
                "source": "demo",
                "document_path": str(pdf),
            },
            tags=["deposition", "question-set"],
        )

    dataset.flush()
    print(f"Inserted {len(build_questions())} rows into {DATASET_NAME}")


if __name__ == "__main__":
    main()
