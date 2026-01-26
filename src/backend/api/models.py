from typing import Literal, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    document_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    assistant_message: str
    span_id: str
    root_span_id: Optional[str] = None


class UploadResponse(BaseModel):
    status: str
    conversation_id: str
    document_id: str


class FeedbackRequest(BaseModel):
    span_id: str
    rating: Optional[Literal["up", "down"]] = None
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str
