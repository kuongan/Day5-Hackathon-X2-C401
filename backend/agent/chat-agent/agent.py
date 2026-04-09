from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langsmith import traceable
from openai import APIConnectionError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from backend.agent.base_agent import BaseAgent
from backend.model.agent.base import BaseAgentState
from backend.model.agent.chat import DiseaseQARequest, DiseaseQAResponse
from backend.utils.short_term_memory import get_short_term_context, record_turn
from prompt import SYSTEM_PROMPT
from tools import retrieve_disease_info


def _collect_sources_from_tool_messages(messages: List[BaseMessage]) -> List[str]:
    sources: List[str] = []
    for message in messages:
        if getattr(message, "type", "") != "tool":
            continue
        content = getattr(message, "content", "")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            continue
        for article in articles:
            if not isinstance(article, dict):
                continue
            source_url = str(article.get("source_url") or "").strip()
            if source_url and source_url not in sources:
                sources.append(source_url)
    return sources


class DiseaseQAAgent(BaseAgent[BaseAgentState]):
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.1, enable_memory: bool = True):
        super().__init__(
            agent_name="disease_qa",
            model_name=model_name,
            temperature=temperature,
            enable_memory=enable_memory,
        )

    def _get_tools(self) -> list[Any]:
        return [retrieve_disease_info]

    def _get_agent_prompt(self) -> str:
        return SYSTEM_PROMPT

    def _create_initial_state(self, query: str, conversation_id: str) -> BaseAgentState:
        return {
            "messages": [HumanMessage(content=query)],
            "user_query": query,
            "agent_type": self.agent_name,
            "conversation_id": conversation_id,
            "metadata": {},
            "error": None,
        }

    def _get_state_type(self):
        return BaseAgentState

    def _add_agent_context(self, messages: List[BaseMessage], state: BaseAgentState) -> List[BaseMessage]:
        if messages and getattr(messages[0], "type", "") == "system":
            return messages
        metadata = dict(state.get("metadata") or {})
        memory_context = str(metadata.get("memory_context") or "").strip()
        system_prompt = self._get_agent_prompt()
        if memory_context:
            system_prompt = f"{system_prompt}\n\n{memory_context}"
        return [SystemMessage(content=system_prompt)] + messages

    def _extract_result(self, state: BaseAgentState) -> DiseaseQAResponse:
        messages = state.get("messages", [])
        answer = "Khong lay duoc cau tra loi."
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                content = str(message.content).strip()
                if content:
                    answer = content
                    break

        sources = _collect_sources_from_tool_messages(messages)
        if sources and "Nguồn:" not in answer:
            answer = f"{answer}\n\nNguồn: {', '.join(sources)}"

        if state.get("error"):
            return DiseaseQAResponse(
                answer=(
                    "Khong the xu ly cau hoi hien tai. "
                    f"Chi tiet: {state['error']}"
                ),
                sources=sources,
            )

        return DiseaseQAResponse(answer=answer, sources=sources)


def build_disease_qa_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.1) -> DiseaseQAAgent:
    return DiseaseQAAgent(model_name=model_name, temperature=temperature)


@traceable(name="ask_disease_question")
def ask_disease_question(question: str, conversation_id: str = "default", memory_context: str = "") -> DiseaseQAResponse:
    request = DiseaseQARequest(question=question)
    try:
        agent = build_disease_qa_agent()
        effective_memory_context = memory_context or get_short_term_context(conversation_id)
        response = agent.process(request.question, memory_context=effective_memory_context)
        record_turn(conversation_id, request.question, response.answer, metadata={"agent": "chat"})
        return response
    except APIConnectionError as exc:
        response = DiseaseQAResponse(
            answer=(
                "Khong the ket noi den OpenAI de tra loi hien tai. "
                "Hay kiem tra ket noi mang, OPENAI_API_KEY va proxy/firewall. "
                f"Chi tiet: {exc}"
            ),
            sources=[],
        )
        record_turn(conversation_id, request.question, response.answer, metadata={"agent": "chat", "error": str(exc)})
        return response
    except Exception as exc:
        response = DiseaseQAResponse(
            answer=f"Khong the xu ly cau hoi hien tai. Chi tiet: {exc}",
            sources=[],
        )
        record_turn(conversation_id, request.question, response.answer, metadata={"agent": "chat", "error": str(exc)})
        return response


def main() -> None:
    sample_query = "Triệu chứng của bệnh sốt xuất huyết là gì?"
    response = ask_disease_question(sample_query)
    print("User:", sample_query)
    print("Assistant:", response.answer)


if __name__ == "__main__":
    main()
