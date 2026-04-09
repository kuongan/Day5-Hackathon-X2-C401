from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question")
    conversation_id: str = Field(default="default", min_length=1)


class BookingResponse(BaseModel):
    success: bool
    answer: str | None = None
    error: str | None = None
    appointment_id: int | None = None
    appointment_details: dict[str, Any] | None = None
