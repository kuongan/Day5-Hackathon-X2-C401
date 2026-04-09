"""
Tools for orchestration agent.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
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
from backend.utils.llm_manager import get_llm


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INTENT_CLASSIFIER_SYSTEM_PROMPT = """
Ban la bo phan phan loai intent cho mot he thong tro ly y te.

Hay doc cau hoi nguoi dung va suy luan theo y nghia, khong dua vao keyword rule co dinh.

Phan loai vao mot trong cac intent sau:
- medicine: hoi ve thuoc, lieu dung, tac dung phu, chi dinh, chong chi dinh, tuong tac, cach dung
- booking: dat lich kham, kiem tra lich, tim bac si, chon khung gio, hoan/huy lich
- chat: Trả lời câu hỏi về cơ thể người và các bệnh, trieu chung, nguyen nhan, phong ngua, dieu tri, tu van suc khoe
- multi: cau hoi can hon mot agent de tra loi day du
- unknown: khong xac dinh duoc intent ro rang

Tra ve confidence trong khoang 0-1 va reasons ngan gon, noi ro vi sao phan loai nhu vay.
""".strip()


ROUTER_SYSTEM_PROMPT = """
Ban la bo phan route cho he thong tro ly y te.

Nhiem vu: dua tren cau hoi nguoi dung va intent hien co, chon nhung agent can goi.
Khong dung rule keyword co dinh. Hay route theo y nghia va muc do phu hop cua tung agent.

Available agents:
- medicine: tra loi ve thuoc, lieu dung, tac dung phu, chi dinh, chong chi dinh
- booking: dat lich, tim bac si, kiem tra lich hen, xu ly khung gio
- chat: hoi ve benh và cơ thể người, trieu chung, nguyen nhan, phong ngua, tu van y khoa, không dùng để trả lời trực tiếp câu hỏi về lịch hoặc thuốc.

Quy tac:
- Co the chon 1 hoac nhieu agent neu cau hoi phuc hop.
- Neu intent hien co khong ro, van duoc phep route toi agent phu hop nhat theo nguyen van.
- Khong de route_to rong neu van co the suy luan ra mot agent phu hop.

Huong dan quan trong de tranh goi agent khong can thiet:
- Neu user dua ra yeu cau hanh dong dat lich ro rang (vi du: "hay dat lich", "dat lich cho toi", "toi muon hen") thi uu tien booking.
- Trong truong hop user nhac ten benh/chuan doan chi de mo ta ly do kham (vi du: "toi bi amidan, dat lich kham...") ma KHONG yeu cau giai thich y khoa, route_to nen chi la ["booking"].
- Chi goi chat khi user co cau hoi thong tin y khoa that su (trieu chung, nguyen nhan, cach dieu tri, co nen lam gi, ...).
- Chi goi medicine khi user hoi ve thuoc hoac lieu dung.

Vi du:
1) "Toi bi amidan, hay dat lich kham voi bac si Nguyen Thanh Liem ngay 12/4 luc 10h" -> route_to: ["booking"]
2) "Toi bi amidan, trieu chung nao can di cap cuu?" -> route_to: ["chat"]
3) "Toi bi amidan, dat lich kham va cho toi biet co nen dung paracetamol khong" -> route_to: ["booking", "medicine"]
""".strip()


def _build_structured_llm():
    return get_llm(model_name="gpt-4o-mini", temperature=0.0)


def _safe_structured_invoke(prompt: str, schema, *, user_query: str, extra_context: str = ""):
    llm = _build_structured_llm()
    structured_llm = llm.with_structured_output(schema)
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"Cau hoi: {user_query}\n{extra_context}".strip()),
    ]
    return structured_llm.invoke(messages)


@tool(args_schema=IntentClassificationInput)
def classify_intent(query: str, context: str = "") -> str:
    """Classify user query using semantic understanding, not keyword rules."""
    try:
        result = _safe_structured_invoke(
            INTENT_CLASSIFIER_SYSTEM_PROMPT,
            IntentClassificationResult,
            user_query=query,
            extra_context=str(context or "").strip(),
        )
        if isinstance(result, IntentClassificationResult):
            result.query = query
            return result.model_dump_json(ensure_ascii=False)
    except Exception as exc:
        fallback = IntentClassificationResult(
            query=query,
            intent=IntentType.UNKNOWN,
            confidence=0.0,
            reasons=[f"Intent classification failed: {exc}"],
        )
        return fallback.model_dump_json(ensure_ascii=False)

    fallback = IntentClassificationResult(
        query=query,
        intent=IntentType.UNKNOWN,
        confidence=0.0,
        reasons=["Intent classification returned an unexpected response"],
    )
    return fallback.model_dump_json(ensure_ascii=False)


@tool(args_schema=RouteDecisionInput)
def route_request(query: str, intent: IntentType, context: str = "") -> str:
    """Route user query to one or more delegated agents using semantic judgment."""
    try:
        result = _safe_structured_invoke(
            ROUTER_SYSTEM_PROMPT,
            RouteDecisionResult,
            user_query=query,
            extra_context=f"Intent hien tai: {intent.value}\n{str(context or '').strip()}",
        )
        if isinstance(result, RouteDecisionResult):
            result.query = query
            result.intent = intent if intent else IntentType.UNKNOWN
            if not result.route_to:
                result.route_to = ["chat"]
            return result.model_dump_json(ensure_ascii=False)
    except Exception as exc:
        fallback = RouteDecisionResult(
            query=query,
            intent=intent,
            route_to=["chat"],
        )
        return fallback.model_dump_json(ensure_ascii=False)

    fallback = RouteDecisionResult(query=query, intent=intent, route_to=["chat"])
    return fallback.model_dump_json(ensure_ascii=False)


def _call_medicine_query(query: str, conversation_id: str, memory_context: str = "") -> DelegatedAgentCallResult:
    try:
        medicine_agent_path = PROJECT_ROOT / "backend" / "agent" / "medicine-agent" / "agent.py"
        medicine_module = _load_module("medicine_agent_runtime", medicine_agent_path)
        response = medicine_module.ask_medicine_question(query, conversation_id=conversation_id, memory_context=memory_context)
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


def _call_chat_query(query: str, conversation_id: str, memory_context: str = "") -> DelegatedAgentCallResult:
    try:
        chat_agent_path = PROJECT_ROOT / "backend" / "agent" / "chat-agent" / "agent.py"
        chat_module = _load_module("chat_agent_runtime", chat_agent_path)
        response = chat_module.ask_disease_question(query, conversation_id=conversation_id, memory_context=memory_context)
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


def _call_medicine_query_with_context(query: str, memory_context: str = "") -> DelegatedAgentCallResult:
    return _call_medicine_query(query, conversation_id="default", memory_context=memory_context)


def _call_chat_query_with_context(query: str, memory_context: str = "") -> DelegatedAgentCallResult:
    return _call_chat_query(query, conversation_id="default", memory_context=memory_context)


def _call_booking_query(query: str, conversation_id: str, context: str = "") -> DelegatedAgentCallResult:
    try:
        from backend.agent.booking_agent.agent import ask_booking_question

        result = ask_booking_question(question=query, conversation_id=conversation_id, memory_context=context)
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
def call_medicine_agent(query: str, conversation_id: str = "default", context: str = "") -> str:
    """Delegate a query to medicine agent and return structured JSON result."""
    _ = conversation_id
    result = _call_medicine_query(query, conversation_id=conversation_id, memory_context=context)
    return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=DelegatedAgentCallInput)
def call_chat_agent(query: str, conversation_id: str = "default", context: str = "") -> str:
    """Delegate a query to chat agent and return structured JSON result."""
    _ = conversation_id
    result = _call_chat_query(query, conversation_id=conversation_id, memory_context=context)
    return result.model_dump_json(ensure_ascii=False)


@tool(args_schema=DelegatedAgentCallInput)
def call_booking_agent(query: str, conversation_id: str = "default", context: str = "") -> str:
    """Delegate a query to booking agent and return structured JSON result."""
    result = _call_booking_query(query, conversation_id, context=context)
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

    if successful:
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
