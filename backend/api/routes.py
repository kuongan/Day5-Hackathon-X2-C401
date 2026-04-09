from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from fastapi import APIRouter, HTTPException

from backend.agent.booking_agent.agent import ask_booking_question
from backend.api.schemas import AgentQuestionRequest, BookingResponse
from backend.model.agent.chat import DiseaseQAResponse
from backend.model.agent.medicine import MedicineQAResponse
from backend.model.agent.oschestration import OrchestrationResponse

router = APIRouter(prefix="/api/v1", tags=["agents"])

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _chat_module() -> ModuleType:
    return _load_module(
        "chat_agent_runtime_api",
        PROJECT_ROOT / "agent" / "chat-agent" / "agent.py",
    )


def _medicine_module() -> ModuleType:
    return _load_module(
        "medicine_agent_runtime_api",
        PROJECT_ROOT / "agent" / "medicine-agent" / "agent.py",
    )


def _orchestration_module() -> ModuleType:
    return _load_module(
        "orchestration_agent_runtime_api",
        PROJECT_ROOT / "agent" / "orchestration-agent" / "agent.py",
    )


@router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=DiseaseQAResponse)
def ask_chat(request: AgentQuestionRequest) -> DiseaseQAResponse:
    try:
        module = _chat_module()
        return module.ask_disease_question(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chat agent failed: {exc}") from exc


@router.post("/medicine", response_model=MedicineQAResponse)
def ask_medicine(request: AgentQuestionRequest) -> MedicineQAResponse:
    try:
        module = _medicine_module()
        return module.ask_medicine_question(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Medicine agent failed: {exc}") from exc


@router.post("/booking", response_model=BookingResponse)
def ask_booking(request: AgentQuestionRequest) -> BookingResponse:
    try:
        result = ask_booking_question(
            question=request.question,
            conversation_id=request.conversation_id,
        )
        payload = dict(getattr(result, "__dict__", {}))
        return BookingResponse(
            success=bool(payload.get("success", False)),
            error=payload.get("error"),
            appointment_id=payload.get("appointment_id"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Booking agent failed: {exc}") from exc


@router.post("/orchestration", response_model=OrchestrationResponse)
def ask_orchestration(request: AgentQuestionRequest) -> OrchestrationResponse:
    try:
        module = _orchestration_module()
        return module.ask_orchestration_question(
            request.question,
            conversation_id=request.conversation_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Orchestration agent failed: {exc}") from exc
