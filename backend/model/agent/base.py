"""
Base models for all agents.
"""
from typing import TypedDict, Optional, Dict, Any, List
from langchain_core.messages import BaseMessage

class BaseAgentState(TypedDict):
    """Base state structure for all agents"""
    messages: List[BaseMessage]
    user_query: str
    agent_type: str
    conversation_id: str
    metadata: Optional[Dict[str, Any]]
    error: Optional[str]

class BaseAgentResult:
    """Base result structure for all agents"""
    def __init__(self, success: bool, error: Optional[str] = None):
        self.success = success
        self.error = error
        self.agent_type = self.__class__.__name__.replace('Result', '').lower()