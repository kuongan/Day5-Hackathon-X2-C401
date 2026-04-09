from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BookingQARequest(BaseModel):
	question: str = Field(..., min_length=1)
	conversation_id: str = Field(default="default", min_length=1)


class BookingQAResponse(BaseModel):
	success: bool
	answer: str
	appointment_id: Optional[int] = None
	appointment_details: Optional[Dict[str, Any]] = None
	error: Optional[str] = None

