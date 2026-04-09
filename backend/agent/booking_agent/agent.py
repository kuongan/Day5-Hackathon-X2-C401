"""
Booking Agent models and implementation.
"""
import logging
from typing import TypedDict, Optional, Dict, Any, List, Type
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from backend.agent.base_agent import BaseAgent
from backend.model.agent.base import BaseAgentState, BaseAgentResult
from . import tools
from .prompts import BOOKING_AGENT_PROMPT

logger = logging.getLogger(__name__)

class BookingAgentState(BaseAgentState):
    """State structure for Booking Agent"""
    doctor_name: Optional[str]
    date: Optional[str]
    time_start: Optional[str]
    patient_info: Optional[Dict[str, Any]]
    appointment_details: Optional[Dict[str, Any]]

class BookingAgentResult(BaseAgentResult):
    """Result structure for Booking Agent"""
    def __init__(self, success: bool, error: Optional[str] = None, appointment_id: Optional[int] = None):
        super().__init__(success, error)
        self.appointment_id = appointment_id

class BookingAgent(BaseAgent[BookingAgentState]):
    """Booking Agent implementation using LangGraph"""

    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0, enable_memory: bool = True):
        super().__init__(
            agent_name="BookingAgent",
            model_name=model_name,
            temperature=temperature,
            enable_memory=enable_memory
        )
        logger.info("BookingAgent initialized with tools: %s", [t.name for t in self.tools])

    def _get_tools(self) -> List[BaseTool]:
        """Get the tools specific to booking agent"""
        return [
            tools.get_doctors,
            tools.check_appointment,
            tools.create_appointment
        ]

    def _get_agent_prompt(self) -> str:
        """Get the booking agent prompt"""
        return BOOKING_AGENT_PROMPT

    def _create_initial_state(self, query: str, conversation_id: str) -> BookingAgentState:
        """Create initial state for booking agent"""
        return BookingAgentState(
            messages=[],
            user_query=query,
            agent_type="booking",
            conversation_id=conversation_id,
            metadata={},
            error=None,
            doctor_name=None,
            date=None,
            time_start=None,
            patient_info=None,
            appointment_details=None
        )

    def _get_state_type(self) -> Type[BookingAgentState]:
        """Get the state type"""
        return BookingAgentState

    def _add_agent_context(self, messages: List[BaseMessage], state: BookingAgentState) -> List[BaseMessage]:
        """Add booking-specific context to messages"""
        system_message = f"{self._get_agent_prompt()}\n\nCurrent booking state: {state}"
        from langchain_core.messages import SystemMessage
        return [SystemMessage(content=system_message)] + messages

    def _update_agent_state(self, state: BookingAgentState, response: BaseMessage) -> BookingAgentState:
        """Update state based on agent response"""
        # Extract booking information from response if available
        if hasattr(response, 'content'):
            content = response.content.lower()
            # Simple extraction - in real implementation, use better NLP
            if 'doctor' in content and not state['doctor_name']:
                # Extract doctor name - placeholder
                pass
        return state

    def _preprocess_tool_args(self, tool_args: Dict[str, Any], state: BookingAgentState) -> Dict[str, Any]:
        """Preprocess tool arguments with state information"""
        # Use state to fill missing args if possible
        if 'doctor_name' not in tool_args and state.get('doctor_name'):
            tool_args['doctor_name'] = state['doctor_name']
        if 'date' not in tool_args and state.get('date'):
            tool_args['date'] = state['date']
        if 'time_start' not in tool_args and state.get('time_start'):
            tool_args['time_start'] = state['time_start']
        return tool_args

    def _process_tool_result(self, state: BookingAgentState, tool_name: str, result: Any) -> BookingAgentState:
        """Process tool results and update state"""
        if tool_name == "create_appointment" and isinstance(result, dict) and result.get('id'):
            state['appointment_details'] = result
        return state

    def _should_continue(self, state: BookingAgentState) -> str:
        """Determine if workflow should continue"""
        last_message = state["messages"][-1] if state["messages"] else None
        if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        if state.get("appointment_details"):
            return "finalize"
        return "end"

    def _finalize_node(self, state: BookingAgentState) -> BookingAgentState:
        """Finalize the booking process"""
        if state.get("appointment_details"):
            success_msg = f"Appointment booked successfully: {state['appointment_details']}"
            from langchain_core.messages import AIMessage
            state["messages"].append(AIMessage(content=success_msg))
        return state

# Example test
if __name__ == "__main__":
    agent = BookingAgent()
    initial_state = agent._create_initial_state("Book an appointment with Dr. Đỗ Tất Cường on 2026-04-08 at 8:00", "test_conv")
    print("Initial state:", initial_state)
    print("Tools:", [t.name for t in agent._get_tools()])
    
    