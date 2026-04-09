from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional, Type

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langsmith import traceable
from openai import APIConnectionError

from backend.agent.base_agent import BaseAgent
from backend.model.agent.base import BaseAgentState
from backend.model.agent.booking import BookingQARequest, BookingQAResponse
from backend.utils.short_term_memory import get_short_term_context, record_turn

from . import tools
from .prompts import BOOKING_AGENT_PROMPT


def _normalize_vietnamese_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    normalized = normalized.replace("đ", "d").replace("Đ", "D")
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(normalized.lower().split())


def _extract_booking_details(question: str) -> Dict[str, str]:
    normalized_question = _normalize_vietnamese_text(question)

    # Try to extract date in multiple formats
    date_str = None
    date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", normalized_question)
    if date_match:
        date_str = date_match.group(1)
    else:
        # Try Vietnamese date format (D/M/YYYY or DD/MM/YYYY)
        date_match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", question)
        if date_match:
            day, month, year = date_match.groups()
            date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    
    time_match = re.search(r"\b(\d{1,2}:\d{2})\b", normalized_question)

    doctor_name = ""
    
    # Try to extract doctor name after "Bác sĩ:" or "bac si" (from confirmation message)
    # This handles format like "Bác sĩ: Nguyễn Quang Lâm"
    doctor_match = re.search(
        r"bac\s+si\s*:?\s*([a-z\s]+?)(?:\s+chuyen\s+khoa|\s+benh\s+vien|,|\n|$)",
        normalized_question,
    )
    if not doctor_match:
        # Fallback to original pattern for natural language like "với bác sĩ X" or "bác sĩ X vào"
        doctor_match = re.search(
            r"(?:voi\s+)?bac\s+si\s+(.+?)(?:\s+vao\s+ngay\s+|\s+vao\s+|\s+luc\s+|\s+ngay\s+\d|$)",
            normalized_question,
        )
    
    if doctor_match:
        candidate = doctor_match.group(1).strip()
        # Clean up the name
        doctor_name = re.sub(r"\s+", " ", candidate).strip()

    return {
        "doctor_name": doctor_name,
        "date": date_str or "",
        "time_start": time_match.group(1) if time_match else "",
    }


def _fill_from_memory(details: Dict[str, str], memory_context: str) -> Dict[str, str]:
    if not memory_context:
        return details

    normalized_memory = _normalize_vietnamese_text(memory_context)
    if not details.get("doctor_name"):
        doctor_match = re.search(
            r"(?:bac\s+si\s+)?([a-z0-9\s.-]{3,60})",
            normalized_memory,
        )
        if doctor_match:
            candidate = doctor_match.group(1).strip()
            if candidate and len(candidate.split()) >= 2:
                details["doctor_name"] = candidate

    if not details.get("date"):
        date_match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", normalized_memory)
        if date_match:
            details["date"] = date_match.group(1)

    if not details.get("time_start"):
        time_match = re.search(r"\b(\d{1,2}:\d{2})\b", normalized_memory)
        if time_match:
            details["time_start"] = time_match.group(1)

    return details


def _is_confirmation_message(question: str) -> bool:
    """Check if user message is confirming booking details"""
    normalized = _normalize_vietnamese_text(question)
    confirmation_patterns = [
        r"xac\s+nhan",
        r"^(co|dung|duoc|ok|co\s+the)",
        r"vang",
        r"dat\s+lich",
        r"thong\s+tin.*dung",
        r"thong\s+tin.*chinh\s+xac"
    ]
    
    return any(re.search(pattern, normalized) for pattern in confirmation_patterns)


class BookingAgentState(BaseAgentState):
    doctor_name: Optional[str]
    date: Optional[str]
    time_start: Optional[str]
    patient_info: Optional[Dict[str, Any]]
    appointment_details: Optional[Dict[str, Any]]


class BookingAgent(BaseAgent[BookingAgentState]):
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0, enable_memory: bool = True):
        super().__init__(
            agent_name="booking",
            model_name=model_name,
            temperature=temperature,
            enable_memory=enable_memory,
        )

    def _get_tools(self) -> List[BaseTool]:
        return [
            tools.get_doctors,
            tools.check_appointment,
            tools.create_appointment,
            tools.seek_doctor_by_disease,
            tools.get_doctor_available_slots,
        ]

    def _get_agent_prompt(self) -> str:
        return BOOKING_AGENT_PROMPT

    def _create_initial_state(self, query: str, conversation_id: str) -> BookingAgentState:
        return {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
            "agent_type": self.agent_name,
            "conversation_id": conversation_id,
            "metadata": {},
            "error": None,
            "doctor_name": None,
            "date": None,
            "time_start": None,
            "patient_info": None,
            "appointment_details": None,
        }

    def _get_state_type(self) -> Type[BookingAgentState]:
        return BookingAgentState

    def _add_agent_context(self, messages: List[BaseMessage], state: BookingAgentState) -> List[BaseMessage]:
        if messages and getattr(messages[0], "type", "") == "system":
            return messages
        metadata = dict(state.get("metadata") or {})
        memory_context = str(metadata.get("memory_context") or "").strip()
        system_prompt = self._get_agent_prompt()
        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}"
        return [SystemMessage(content=system_prompt)] + messages

    def _preprocess_tool_args(self, tool_args: Dict[str, Any], state: BookingAgentState, tool_name: str | None = None) -> Dict[str, Any]:
        if "doctor_name" not in tool_args and state.get("doctor_name"):
            tool_args["doctor_name"] = state["doctor_name"]
        if "date" not in tool_args and state.get("date"):
            tool_args["date"] = state["date"]
        if "time_start" not in tool_args and state.get("time_start"):
            tool_args["time_start"] = state["time_start"]
        return tool_args

    def _process_tool_result(self, state: BookingAgentState, tool_name: str, result: Any) -> BookingAgentState:
        if tool_name == "create_appointment" and isinstance(result, dict) and result.get("id"):
            state["appointment_details"] = result
        return state

    def _extract_result(self, state: BookingAgentState) -> BookingQAResponse:
        appointment_details = state.get("appointment_details")
        appointment_id = None
        if isinstance(appointment_details, dict):
            raw_id = appointment_details.get("id")
            appointment_id = int(raw_id) if isinstance(raw_id, int) else None

        answer = "Khong the xu ly yeu cau dat lich hien tai."
        messages = state.get("messages", [])
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                content = str(message.content).strip()
                if content and content != "Completed successfully":
                    answer = content
                    break

        if state.get("error"):
            return BookingQAResponse(
                success=False,
                answer=f"Khong the dat lich hien tai. Chi tiet: {state['error']}",
                appointment_id=appointment_id,
                appointment_details=appointment_details,
                error=state.get("error"),
            )

        if appointment_id and answer == "Khong the xu ly yeu cau dat lich hien tai.":
            answer = f"Dat lich thanh cong. appointment_id={appointment_id}"

        return BookingQAResponse(
            success=bool(appointment_id),
            answer=answer,
            appointment_id=appointment_id,
            appointment_details=appointment_details,
            error=None,
        )


def build_booking_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.0) -> BookingAgent:
    return BookingAgent(model_name=model_name, temperature=temperature)


@traceable(name="ask_booking_question")
def ask_booking_question(question: str, conversation_id: str = "default", memory_context: str = "") -> BookingQAResponse:
    request = BookingQARequest(question=question, conversation_id=conversation_id)
    try:
        effective_memory_context = memory_context or get_short_term_context(conversation_id)
        booking_details = _extract_booking_details(request.question)
        booking_details = _fill_from_memory(booking_details, effective_memory_context)
        if booking_details["doctor_name"] and booking_details["date"] and booking_details["time_start"]:
            direct_result = tools.create_appointment.invoke(booking_details)
            if isinstance(direct_result, dict) and direct_result.get("id"):
                response = BookingQAResponse(
                    success=True,
                    answer=(
                        f"Lich hen kham voi bac si {direct_result.get('doctor_name', booking_details['doctor_name'])} "
                        f"vao ngay {direct_result.get('date', booking_details['date'])} luc {direct_result.get('time_start', booking_details['time_start'])} "
                        "da duoc dat thanh cong."
                    ),
                    appointment_id=int(direct_result["id"]),
                    appointment_details=direct_result,
                    error=None,
                )
                record_turn(conversation_id, request.question, response.answer, metadata={"agent": "booking", **direct_result})
                return response

        agent = build_booking_agent()
        result = agent.process(
            query=request.question,
            conversation_id=request.conversation_id,
            memory_context=effective_memory_context,
        )
        if result.success and result.appointment_id:
            record_turn(conversation_id, request.question, result.answer, metadata={"agent": "booking", "appointment_id": result.appointment_id})
            return result

        record_turn(conversation_id, request.question, result.answer, metadata={"agent": "booking", "success": result.success})
        return result
    except APIConnectionError as exc:
        response = BookingQAResponse(
            success=False,
            answer=(
                "Khong the ket noi den OpenAI de xu ly yeu cau dat lich hien tai. "
                f"Chi tiet: {exc}"
            ),
            appointment_id=None,
            appointment_details=None,
            error=str(exc),
        )
        record_turn(conversation_id, request.question, response.answer, metadata={"agent": "booking", "error": str(exc)})
        return response
    except Exception as exc:
        response = BookingQAResponse(
            success=False,
            answer=f"Khong the xu ly yeu cau dat lich hien tai. Chi tiet: {exc}",
            appointment_id=None,
            appointment_details=None,
            error=str(exc),
        )
        record_turn(conversation_id, request.question, response.answer, metadata={"agent": "booking", "error": str(exc)})
        return response


if __name__ == "__main__":
    sample_query = "Toi muon dat lich kham voi bac si Do Tat Cuong vao ngay 2026-04-09 luc 08:00"
    response = ask_booking_question(sample_query, conversation_id="booking_test")
    print("User:", sample_query)
    print("Assistant:", response.answer)
    print("Success:", response.success)
    if response.appointment_id:
        print("Appointment ID:", response.appointment_id)
