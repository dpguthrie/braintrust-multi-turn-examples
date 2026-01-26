import os
from functools import lru_cache

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


DATA_PATH = os.getenv("DEPOSITION_SAMPLE_PATH", "./data/sample_deposition.txt")


def _load_documents(path: str) -> list[str]:
    if path.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires pypdf. Add it to dependencies and reinstall."
            ) from exc

        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        return ["\n\n".join(pages)]

    with open(path, "r", encoding="utf-8", errors="ignore") as file:
        return [file.read()]


@lru_cache(maxsize=8)
def get_vectorstore(path: str) -> FAISS:
    docs = _load_documents(path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=40)
    chunks = splitter.create_documents(docs)
    embeddings = OpenAIEmbeddings()
    return FAISS.from_documents(chunks, embeddings)


def retrieve_context(query: str, k: int = 3, path: str | None = None) -> str:
    doc_path = path or DATA_PATH
    vectorstore = get_vectorstore(doc_path)
    results = vectorstore.similarity_search(query, k=k)
    return "\n\n".join([doc.page_content for doc in results])
