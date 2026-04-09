"""
Orchestration agent implementation.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langsmith import traceable
from openai import APIConnectionError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.base_agent import BaseAgent
from backend.model.agent.base import BaseAgentState
from backend.model.agent.oschestration import (
    DelegatedAgentCallResult,
    IntentType,
    OrchestrationRequest,
    OrchestrationResponse,
)

CURRENT_DIR = Path(__file__).resolve().parent


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {module_name} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prompt_module = _load_module("orchestration_prompt", CURRENT_DIR / "prompt.py")
tools_module = _load_module("orchestration_tools", CURRENT_DIR / "tools.py")

SYSTEM_PROMPT = prompt_module.SYSTEM_PROMPT

classify_intent = tools_module.classify_intent
route_request = tools_module.route_request
call_medicine_agent = tools_module.call_medicine_agent
call_booking_agent = tools_module.call_booking_agent
call_chat_agent = tools_module.call_chat_agent
aggregate_results = tools_module.aggregate_results


def _json_load_safe(content: Any) -> Dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return {}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class OrchestrationAgent(BaseAgent[BaseAgentState]):
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0, enable_memory: bool = True):
        super().__init__(
            agent_name="orchestration",
            model_name=model_name,
            temperature=temperature,
            enable_memory=enable_memory,
        )

    def _get_tools(self) -> list[Any]:
        return [
            classify_intent,
            route_request,
            call_medicine_agent,
            call_booking_agent,
            call_chat_agent,
            aggregate_results,
        ]

    def _get_agent_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _create_initial_state(self, query: str, conversation_id: str) -> BaseAgentState:
        return {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
            "agent_type": self.agent_name,
            "conversation_id": conversation_id,
            "metadata": {"orchestration": {}},
            "error": None,
        }

    def _get_state_type(self):
        return BaseAgentState

    def _add_agent_context(self, messages: List[BaseMessage], state: BaseAgentState) -> List[BaseMessage]:
        if messages and getattr(messages[0], "type", "") == "system":
            return messages
        return [SystemMessage(content=self._get_agent_prompt())] + messages

    def _process_tool_result(self, state: BaseAgentState, tool_name: str, result: Any) -> BaseAgentState:
        metadata = dict(state.get("metadata") or {})
        orchestration = dict(metadata.get("orchestration") or {})

        payload = _json_load_safe(result)

        if tool_name == "classify_intent":
            orchestration["intent"] = payload.get("intent", IntentType.UNKNOWN.value)
        elif tool_name == "route_request":
            orchestration["route_to"] = payload.get("route_to", [])
        elif tool_name in {"call_medicine_agent", "call_booking_agent", "call_chat_agent"}:
            delegated_results = list(orchestration.get("delegated_results") or [])
            delegated_results.append(payload)
            orchestration["delegated_results"] = delegated_results
        elif tool_name == "aggregate_results":
            orchestration["aggregated_answer"] = payload.get("answer", "")

        metadata["orchestration"] = orchestration
        state["metadata"] = metadata
        return state

    def _extract_result(self, state: BaseAgentState) -> OrchestrationResponse:
        metadata = dict(state.get("metadata") or {})
        orchestration = dict(metadata.get("orchestration") or {})

        intent_raw = str(orchestration.get("intent", IntentType.UNKNOWN.value)).lower()
        try:
            intent = IntentType(intent_raw)
        except ValueError:
            intent = IntentType.UNKNOWN

        route_to = orchestration.get("route_to", [])
        if not isinstance(route_to, list):
            route_to = []

        delegated_results_payload = orchestration.get("delegated_results", [])
        delegated_results: List[DelegatedAgentCallResult] = []
        if isinstance(delegated_results_payload, list):
            for item in delegated_results_payload:
                if isinstance(item, dict):
                    try:
                        delegated_results.append(DelegatedAgentCallResult.model_validate(item))
                    except Exception:
                        continue

        answer = str(orchestration.get("aggregated_answer") or "").strip()
        if not answer:
            messages = state.get("messages", [])
            for message in reversed(messages):
                if isinstance(message, AIMessage):
                    content = str(message.content).strip()
                    if content and content != "Completed successfully":
                        answer = content
                        break

        if not answer:
            answer = "Khong the tong hop ket qua luc nay."

        if state.get("error"):
            return OrchestrationResponse(
                answer=f"Khong the xu ly yeu cau. Chi tiet: {state['error']}",
                intent=intent,
                route_to=route_to,
                delegated_results=delegated_results,
                error=state.get("error"),
            )

        return OrchestrationResponse(
            answer=answer,
            intent=intent,
            route_to=route_to,
            delegated_results=delegated_results,
            error=None,
        )


def build_orchestration_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.0) -> OrchestrationAgent:
    return OrchestrationAgent(model_name=model_name, temperature=temperature)


@traceable(name="ask_orchestration_question")
def ask_orchestration_question(question: str, conversation_id: str = "default") -> OrchestrationResponse:
    request = OrchestrationRequest(question=question, conversation_id=conversation_id)
    try:
        agent = build_orchestration_agent()
        return agent.process(query=request.question, conversation_id=request.conversation_id)
    except APIConnectionError as exc:
        return OrchestrationResponse(
            answer=(
                "Khong the ket noi den OpenAI de xu ly yeu cau hien tai. "
                f"Chi tiet: {exc}"
            ),
            intent=IntentType.UNKNOWN,
            route_to=[],
            delegated_results=[],
            error=str(exc),
        )
    except Exception as exc:
        return OrchestrationResponse(
            answer=f"Khong the xu ly yeu cau hien tai. Chi tiet: {exc}",
            intent=IntentType.UNKNOWN,
            route_to=[],
            delegated_results=[],
            error=str(exc),
        )


if __name__ == "__main__":
    samples = [
        "Toi can biet lieu dung paracetamol",
        "Toi muon dat lich kham vao ngay mai luc 9h",
        "Trieu chung cua sot xuat huyet la gi?",
        "Toi muon dat lich va hoi tac dung phu cua aspirin",
    ]

    for idx, query in enumerate(samples, start=1):
        print(f"\n[TEST {idx}] Query: {query}")
        resp = ask_orchestration_question(query, conversation_id="orch_test")
        print(f"Intent: {resp.intent.value}")
        print(f"Route: {resp.route_to}")
        print(f"Answer: {resp.answer[:400]}")
        print(f"Delegated results: {len(resp.delegated_results)}")
        if resp.error:
            print(f"Error: {resp.error}")
