"""
Medicine QA Agent for drug information queries.
Uses FAISS vector search to find medicines by name or indication.
"""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys
from typing import Any, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langsmith import traceable
from openai import APIConnectionError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from backend.agent.base_agent import BaseAgent
from backend.model.agent.base import BaseAgentState
from backend.model.agent.medicine import MedicineQARequest, MedicineQAResponse
from backend.utils.short_term_memory import get_short_term_context, record_turn

# Load modules with hyphenated names using importlib
CURRENT_DIR = Path(__file__).resolve().parent

# Load prompt
prompt_path = CURRENT_DIR / "prompt.py"
spec_prompt = importlib.util.spec_from_file_location("medicine_agent_prompt", prompt_path)
prompt_module = importlib.util.module_from_spec(spec_prompt)
spec_prompt.loader.exec_module(prompt_module)
SYSTEM_PROMPT = prompt_module.SYSTEM_PROMPT

# Load tools
tools_path = CURRENT_DIR / "tools.py"
spec_tools = importlib.util.spec_from_file_location("medicine_agent_tools", tools_path)
tools_module = importlib.util.module_from_spec(spec_tools)
spec_tools.loader.exec_module(tools_module)
get_drug_info = tools_module.get_drug_info
get_dosage = tools_module.get_dosage
get_drugs_by_indication = tools_module.get_drugs_by_indication
get_contraindications = tools_module.get_contraindications
get_side_effects = tools_module.get_side_effects


def _collect_sources_from_tool_messages(messages: List[BaseMessage]) -> List[str]:
	"""Extract medicine URLs from tool results"""
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
		
		# Extract from medicines list
		medicines = payload.get("medicines", [])
		if isinstance(medicines, list):
			for med in medicines:
				if isinstance(med, dict):
					url = str(med.get("url", "")).strip()
					if url and url not in sources:
						sources.append(url)
	return sources


class MedicineQAAgent(BaseAgent[BaseAgentState]):
	"""
	Agent for medicine/drug information queries.
	Retrieves drug info, dosage, indications, contraindications, and side effects.
	"""
	
	def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0, enable_memory: bool = True):
		super().__init__(
			agent_name="medicine_qa",
			model_name=model_name,
			temperature=temperature,
			enable_memory=enable_memory,
		)

	def _get_tools(self) -> list[Any]:
		"""Return all medicine query tools"""
		return [
			get_drug_info,
			get_dosage,
			get_drugs_by_indication,
			get_contraindications,
			get_side_effects,
		]

	def _get_agent_prompt(self) -> str:
		"""Get medicine agent system prompt"""
		return SYSTEM_PROMPT

	def _create_initial_state(self, query: str, conversation_id: str) -> BaseAgentState:
		"""Create initial state for medicine QA query"""
		return {
			"messages": [HumanMessage(content=query)],
			"user_query": query,
			"agent_type": self.agent_name,
			"conversation_id": conversation_id,
			"metadata": {},
			"error": None,
		}

	def _get_state_type(self):
		"""Return the state type for this agent"""
		return BaseAgentState

	def _add_agent_context(self, messages: List[BaseMessage], state: BaseAgentState) -> List[BaseMessage]:
		"""Add system context to messages"""
		if messages and getattr(messages[0], "type", "") == "system":
			return messages
		metadata = dict(state.get("metadata") or {})
		memory_context = str(metadata.get("memory_context") or "").strip()
		system_prompt = self._get_agent_prompt()
		if memory_context:
			system_prompt = f"{system_prompt}\n\n{memory_context}"
		return [SystemMessage(content=system_prompt)] + messages

	def _extract_result(self, state: BaseAgentState) -> MedicineQAResponse:
		"""Extract structured result from final agent state"""
		messages = state.get("messages", [])
		answer = "Không lấy được câu trả lời."
		
		# Find last AI message
		for message in reversed(messages):
			if isinstance(message, AIMessage):
				content = str(message.content).strip()
				if content:
					answer = content
					break

		sources = _collect_sources_from_tool_messages(messages)
		
		if state.get("error"):
			return MedicineQAResponse(
				answer=(
					"Không thể xử lý câu hỏi hiện tại. "
					f"Chi tiết: {state['error']}"
				),
				sources=sources,
			)

		return MedicineQAResponse(answer=answer, sources=sources)


def build_medicine_qa_agent(model_name: str = "gpt-4o-mini", temperature: float = 0.0) -> MedicineQAAgent:
	"""Factory function to create and return MedicineQAAgent instance"""
	return MedicineQAAgent(model_name=model_name, temperature=temperature)


@traceable(name="ask_medicine_question")
def ask_medicine_question(question: str, conversation_id: str = "default", memory_context: str = "") -> MedicineQAResponse:
	"""
	Ask a question about medicines/drugs.
	
	Args:
		question: User question about medicines (e.g., drug name, indication, dosage, side effects)
	
	Returns:
		MedicineQAResponse with answer and sources
	"""
	request = MedicineQARequest(question=question)
	try:
		agent = build_medicine_qa_agent()
		effective_memory_context = memory_context or get_short_term_context(conversation_id)
		response = agent.process(request.question, memory_context=effective_memory_context)
		record_turn(conversation_id, request.question, response.answer, metadata={"agent": "medicine"})
		return response
	except APIConnectionError as exc:
		response = MedicineQAResponse(
			answer=(
				"Không thể kết nối đến OpenAI để trả lời hiện tại. "
				"Hãy kiểm tra kết nối mạng, OPENAI_API_KEY và proxy/firewall. "
				f"Chi tiết: {exc}"
			),
			sources=[],
		)
		record_turn(conversation_id, request.question, response.answer, metadata={"agent": "medicine", "error": str(exc)})
		return response
	except Exception as exc:
		response = MedicineQAResponse(
			answer=f"Không thể xử lý câu hỏi hiện tại. Chi tiết: {exc}",
			sources=[],
		)
		record_turn(conversation_id, request.question, response.answer, metadata={"agent": "medicine", "error": str(exc)})
		return response


def main() -> None:
	"""Simple test function"""
	sample_queries = [
		"Thông tin về thuốc paracetamol là gì?",
		"Liều lượng paracetamol như thế nào?",
		"Thuốc nào dùng để hạ sốt cao?",
	]
	
	for query in sample_queries:
		print(f"\nUser: {query}")
		response = ask_medicine_question(query)
		print(f"Assistant: {response.answer}")
		if response.sources:
			print(f"Sources: {', '.join(response.sources[:2])}")


if __name__ == "__main__":
	main()
