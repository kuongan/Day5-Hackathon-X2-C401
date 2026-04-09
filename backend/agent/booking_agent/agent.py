from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langsmith import traceable
from openai import APIConnectionError

from backend.agent.base_agent import BaseAgent
from backend.model.agent.base import BaseAgentState
from backend.model.agent.booking import BookingQARequest, BookingQAResponse

from . import tools
from .prompts import BOOKING_AGENT_PROMPT


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
        return [SystemMessage(content=self._get_agent_prompt())] + messages

    def _preprocess_tool_args(self, tool_args: Dict[str, Any], state: BookingAgentState) -> Dict[str, Any]:
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
def ask_booking_question(question: str, conversation_id: str = "default") -> BookingQAResponse:
    request = BookingQARequest(question=question, conversation_id=conversation_id)
    try:
        agent = build_booking_agent()
        return agent.process(query=request.question, conversation_id=request.conversation_id)
    except APIConnectionError as exc:
        return BookingQAResponse(
            success=False,
            answer=(
                "Khong the ket noi den OpenAI de xu ly yeu cau dat lich hien tai. "
                f"Chi tiet: {exc}"
            ),
            appointment_id=None,
            appointment_details=None,
            error=str(exc),
        )
    except Exception as exc:
        return BookingQAResponse(
            success=False,
            answer=f"Khong the xu ly yeu cau dat lich hien tai. Chi tiet: {exc}",
            appointment_id=None,
            appointment_details=None,
            error=str(exc),
        )


if __name__ == "__main__":
    sample_query = "Toi muon dat lich kham voi bac si Do Tat Cuong vao ngay 2026-04-08 luc 08:00"
    response = ask_booking_question(sample_query, conversation_id="booking_test")
    print("User:", sample_query)
    print("Assistant:", response.answer)
    print("Success:", response.success)
    if response.appointment_id:
        print("Appointment ID:", response.appointment_id)
