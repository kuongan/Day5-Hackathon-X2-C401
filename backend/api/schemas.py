from __future__ import annotations

from pydantic import BaseModel, Field


class AgentQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    conversation_id: str = Field(default="default", min_length=1)


class BookingResponse(BaseModel):
    success: bool
    error: str | None = None
    appointment_id: int | None = None
