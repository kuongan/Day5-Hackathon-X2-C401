"""
Tools for orchestration agent.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
import sys
from typing import Dict, List

from langchain_core.tools import tool

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.model.agent.oschestration import (
    AggregateResultsInput,
    AggregateResultsOutput,
    DelegatedAgentCallInput,
    DelegatedAgentCallResult,
    IntentClassificationInput,
    IntentClassificationResult,
    IntentType,
    RouteDecisionInput,
    RouteDecisionResult,
)


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _count_keywords(query: str, keywords: List[str]) -> int:
    score = 0
    for word in keywords:
        if word in query:
            score += 1
    return score


def _intent_scores(query: str) -> Dict[IntentType, int]:
    q = _normalize(query)

    medicine_keywords = [
        "thuoc", "lieu", "dosage", "tac dung phu", "contra", "indication",
        "aspirin", "paracetamol", "ibuprofen", "amoxicillin",
    ]
    booking_keywords = [
        "dat lich", "hen", "kham", "bac si", "doctor", "appointment", "lich",
        "gio", "ngay", "slot",
    ]
    chat_keywords = [
        "benh", "trieu chung", "nguyen nhan", "phong ngua", "dieu tri",
        "sot xuat huyet", "tieu duong", "cao huyet ap", "viem",
    ]

    return {
        IntentType.MEDICINE: _count_keywords(q, medicine_keywords),
        IntentType.BOOKING: _count_keywords(q, booking_keywords),
        IntentType.CHAT: _count_keywords(q, chat_keywords),
    }


@tool(args_schema=IntentClassificationInput)
def classify_intent(query: str) -> str:
    """Classify user query into medicine, booking, chat, multi, or unknown."""
    scores = _intent_scores(query)
    non_zero = [intent for intent, score in scores.items() if score > 0]

    if len(non_zero) == 0:
        result = IntentClassificationResult(
            query=query,
            intent=IntentType.UNKNOWN,
            confidence=0.2,
            reasons=["No clear keyword signal found"],
        )
        return result.model_dump_json(ensure_ascii=False)

    if len(non_zero) >= 2:
        reasons = [f"{intent.value}: {scores[intent]}" for intent in non_zero]
        result = IntentClassificationResult(
            query=query,
            intent=IntentType.MULTI,
            confidence=0.75,
            reasons=["Multiple intent groups matched"] + reasons,
        )
        return result.model_dump_json(ensure_ascii=False)

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]
    total = sum(scores.values())
    confidence = min(0.95, 0.5 + (best_score / max(total, 1)) * 0.45)

    result = IntentClassificationResult(
        query=query,
        intent=best_intent,
        confidence=confidence,
        reasons=[f"Top score for {best_intent.value}: {best_score}"],
    )
    return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=RouteDecisionInput)
def route_request(query: str, intent: IntentType) -> str:
    """Route user query to one or more delegated agents based on intent."""
    if intent == IntentType.MEDICINE:
        route_to = ["medicine"]
    elif intent == IntentType.BOOKING:
        route_to = ["booking"]
    elif intent == IntentType.CHAT:
        route_to = ["chat"]
    elif intent == IntentType.MULTI:
        route_to = ["medicine", "booking", "chat"]
    else:
        route_to = ["chat"]

    result = RouteDecisionResult(query=query, intent=intent, route_to=route_to)
    return result.model_dump_json(ensure_ascii=False)


def _call_medicine_query(query: str) -> DelegatedAgentCallResult:
    try:
        medicine_agent_path = PROJECT_ROOT / "backend" / "agent" / "medicine-agent" / "agent.py"
        medicine_module = _load_module("medicine_agent_runtime", medicine_agent_path)
        response = medicine_module.ask_medicine_question(query)
        return DelegatedAgentCallResult(
            agent="medicine",
            success=True,
            answer=str(getattr(response, "answer", "")),
            sources=list(getattr(response, "sources", []) or []),
            raw={
                "answer": str(getattr(response, "answer", "")),
                "sources": list(getattr(response, "sources", []) or []),
            },
        )
    except Exception as exc:
        return DelegatedAgentCallResult(
            agent="medicine",
            success=False,
            answer="",
            sources=[],
            error=str(exc),
            raw=None,
        )


def _call_chat_query(query: str) -> DelegatedAgentCallResult:
    try:
        chat_agent_path = PROJECT_ROOT / "backend" / "agent" / "chat-agent" / "agent.py"
        chat_module = _load_module("chat_agent_runtime", chat_agent_path)
        response = chat_module.ask_disease_question(query)
        return DelegatedAgentCallResult(
            agent="chat",
            success=True,
            answer=str(getattr(response, "answer", "")),
            sources=list(getattr(response, "sources", []) or []),
            raw={
                "answer": str(getattr(response, "answer", "")),
                "sources": list(getattr(response, "sources", []) or []),
            },
        )
    except Exception as exc:
        return DelegatedAgentCallResult(
            agent="chat",
            success=False,
            answer="",
            sources=[],
            error=str(exc),
            raw=None,
        )


def _call_booking_query(query: str, conversation_id: str) -> DelegatedAgentCallResult:
    try:
        from backend.agent.booking_agent.agent import ask_booking_question

        result = ask_booking_question(question=query, conversation_id=conversation_id)
        payload = dict(getattr(result, "__dict__", {}))
        success = bool(payload.get("success", False))
        answer = str(payload.get("answer") or "Booking request processed.")
        if payload.get("appointment_id"):
            answer = f"Booking success. appointment_id={payload['appointment_id']}"
        elif payload.get("error"):
            answer = f"Booking failed: {payload['error']}"

        return DelegatedAgentCallResult(
            agent="booking",
            success=success,
            answer=answer,
            sources=[],
            error=payload.get("error"),
            raw=payload,
        )
    except Exception as exc:
        return DelegatedAgentCallResult(
            agent="booking",
            success=False,
            answer="",
            sources=[],
            error=str(exc),
            raw=None,
        )


@tool(args_schema=DelegatedAgentCallInput)
def call_medicine_agent(query: str, conversation_id: str = "default") -> str:
    """Delegate a query to medicine agent and return structured JSON result."""
    _ = conversation_id
    result = _call_medicine_query(query)
    return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=DelegatedAgentCallInput)
def call_chat_agent(query: str, conversation_id: str = "default") -> str:
    """Delegate a query to chat agent and return structured JSON result."""
    _ = conversation_id
    result = _call_chat_query(query)
    return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=DelegatedAgentCallInput)
def call_booking_agent(query: str, conversation_id: str = "default") -> str:
    """Delegate a query to booking agent and return structured JSON result."""
    result = _call_booking_query(query, conversation_id)
    return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=AggregateResultsInput)
def aggregate_results(
    query: str,
    intent: IntentType,
    route_to: List[str],
    delegated_results: List[DelegatedAgentCallResult],
) -> str:
    """Aggregate delegated agent results into final concise answer."""
    if not delegated_results:
        output = AggregateResultsOutput(
            answer="Chua co ket qua tu delegated agents. Vui long thu lai voi cau hoi ro hon."
        )
        return output.model_dump_json(ensure_ascii=False)

    successful = [res for res in delegated_results if res.success and res.answer.strip()]
    failed = [res for res in delegated_results if not res.success]

    lines: List[str] = []
    lines.append(f"Yeu cau: {query}")
    lines.append(f"Intent: {intent.value}")
    lines.append(f"Route: {', '.join(route_to) if route_to else 'none'}")

    if successful:
        lines.append("Ket qua chinh:")
        for item in successful:
            lines.append(f"- [{item.agent}] {item.answer}")

    if failed:
        lines.append("Luu y loi:")
        for item in failed:
            err = item.error or "unknown error"
            lines.append(f"- [{item.agent}] {err}")

    final_answer = "\n".join(lines)
    output = AggregateResultsOutput(answer=final_answer)
    return output.model_dump_json(ensure_ascii=False)


if __name__ == "__main__":
    sample_query = "Toi muon dat lich va hoi lieu dung aspirin"

    print("[TEST] classify_intent")
    intent_json = classify_intent.invoke({"query": sample_query})
    print(intent_json)

    intent_payload = json.loads(intent_json)

    print("\n[TEST] route_request")
    route_json = route_request.invoke({
        "query": sample_query,
        "intent": intent_payload["intent"],
    })
    print(route_json)

    print("\n[TEST] delegated calls")
    print(call_chat_agent.invoke({"query": "Trieu chung sot xuat huyet la gi?"}))
    print(call_medicine_agent.invoke({"query": "Lieu dung paracetamol"}))
    print(call_booking_agent.invoke({"query": "Dat lich kham bac si vao ngay mai", "conversation_id": "test_orch"}))

    print("\n[TEST] aggregate_results")
    aggregate_json = aggregate_results.invoke({
        "query": sample_query,
        "intent": "multi",
        "route_to": ["medicine", "booking", "chat"],
        "delegated_results": [
            {
                "agent": "medicine",
                "success": True,
                "answer": "Paracetamol co tac dung ha sot.",
                "sources": [],
                "error": None,
                "raw": None,
            },
            {
                "agent": "booking",
                "success": False,
                "answer": "",
                "sources": [],
                "error": "Missing date/time",
                "raw": None,
            },
        ],
    })
    print(aggregate_json)
