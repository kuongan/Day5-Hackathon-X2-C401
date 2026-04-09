import logging
from backend.agent.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class BookingAgent(BaseAgent[BookingAgentState]):
    def __init__(self, model_name: str = "gemini-3-flash-preview", temperature: float = 0.0):
        logger.info("BookingAgent initialized with tools: %s", [t.name for t in self.tools])
        
    