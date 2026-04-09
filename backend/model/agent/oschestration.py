"""
Pydantic models for orchestration agent.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    MEDICINE = "medicine"
    BOOKING = "booking"
    CHAT = "chat"
    MULTI = "multi"
    UNKNOWN = "unknown"


class IntentClassificationInput(BaseModel):
    query: str = Field(..., min_length=1, description="User query to classify")


class IntentClassificationResult(BaseModel):
    query: str
    intent: IntentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)


class RouteDecisionInput(BaseModel):
    query: str = Field(..., min_length=1)
    intent: IntentType


class RouteDecisionResult(BaseModel):
    query: str
    intent: IntentType
    route_to: List[str] = Field(default_factory=list)


class DelegatedAgentCallInput(BaseModel):
    query: str = Field(..., min_length=1)
    conversation_id: str = Field(default="default")


class DelegatedAgentCallResult(BaseModel):
    agent: str
    success: bool
    answer: str = ""
    sources: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class AggregateResultsInput(BaseModel):
    query: str = Field(..., min_length=1)
    intent: IntentType
    route_to: List[str] = Field(default_factory=list)
    delegated_results: List[DelegatedAgentCallResult] = Field(default_factory=list)


class AggregateResultsOutput(BaseModel):
    answer: str


class OrchestrationRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str = Field(default="default")


class OrchestrationResponse(BaseModel):
    answer: str
    intent: IntentType = IntentType.UNKNOWN
    route_to: List[str] = Field(default_factory=list)
    delegated_results: List[DelegatedAgentCallResult] = Field(default_factory=list)
    error: Optional[str] = None
