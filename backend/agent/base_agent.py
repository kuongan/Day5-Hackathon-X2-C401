import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, TypeVar, Generic, Type

from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langchain_core.tools import BaseTool
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.utils.llm_manager import get_llm
from backend.model.agent import BaseAgentState, BaseAgentResult


logger = logging.getLogger(__name__)

T = TypeVar('T', bound='BaseAgentState')

class BaseAgent(Generic[T], ABC):
    """
    Abstract base class for all LangGraph agents
    
    Provides common functionality:
    - LangGraph StateGraph setup
    - Tool binding and execution
    - Message handling patterns
    - Memory management
    - Error handling
    - Conversation persistence
    """
    
    def __init__(
        self, 
        agent_name: str,
        model_name: str = "gpt-4o-mini", 
        temperature: float = 0.0,
        enable_memory: bool = True
    ):
        self.agent_name = agent_name
        self.model_name = model_name
        self.temperature = temperature
        self.enable_memory = enable_memory
        self.memory = MemorySaver() if enable_memory else None
        self.llm = self._initialize_llm()
        self.tools = self._get_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm
        self.graph = self._create_graph()
        
        logger.info(f"{self.agent_name} initialized with {len(self.tools)} tools")
    
    def _initialize_llm(self) -> BaseChatModel:
        """Initialize the language model"""
        try:
            return get_llm(model_name=self.model_name, temperature=self.temperature)
        except Exception as e:
            logger.error(f"Failed to initialize LLM for {self.agent_name}: {e}")
            raise
    
    @abstractmethod
    def _get_tools(self) -> List[BaseTool]:
        """Get the tools specific to this agent"""
        pass
    
    @abstractmethod
    def _get_agent_prompt(self) -> str:
        """Get the agent-specific prompt"""
        pass
    
    @abstractmethod
    def _create_initial_state(self, query: str, conversation_id: str) -> T:
        """Create the initial state for this agent"""
        pass
    
    @abstractmethod
    def _get_state_type(self) -> Type[T]:
        """Get the state type for this agent"""
        pass

    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow - common pattern for all agents"""
        workflow = StateGraph(self._get_state_type())

        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)
        workflow.add_node("finalize", self._finalize_node)
        workflow.set_entry_point("agent")

        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "finalize": "finalize",
                "end": END
            }
        )
        
        workflow.add_edge("tools", "agent")
        workflow.add_edge("finalize", END)
        checkpointer = self.memory if self.enable_memory else None
        return workflow.compile(checkpointer=checkpointer)
    
    def _agent_node(self, state: T) -> T:
        """
        Agent reasoning and tool calling node
        Common pattern for all agents with agent-specific customization
        """
        try:
            # Get current messages
            messages = state["messages"]
            messages = self._add_agent_context(messages, state)
            response = self.llm_with_tools.invoke(messages)
            updated_messages = messages + [response]
            state["messages"] = updated_messages
            state = self._update_agent_state(state, response)
            return state
            
        except Exception as e:
            logger.error(f"Error in {self.agent_name} agent node: {e}")
            error_message = AIMessage(content=f"Error in {self.agent_name}: {str(e)}")
            state["messages"] = state["messages"] + [error_message]
            state["error"] = str(e)
            return state
    
    def _tools_node(self, state: T) -> T:
        """
        Execute tools and return results (minimal version with hook for result processing)
        """
        last_message = state["messages"][-1]
        tool_messages = []

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                logger.info(f"Executing {self.agent_name} tool: {tool_name}")
                tool_function = next((t for t in self.tools if t.name == tool_name), None)

                if tool_function:
                    tool_args = self._preprocess_tool_args(tool_args, state)
                    result = tool_function.invoke(tool_args)
                    tool_messages.append(
                        ToolMessage(content=str(result), tool_call_id=tool_call["id"])
                    )
                    
                    state = self._process_tool_result(state, tool_name, result)
                else:
                    msg = f"Tool {tool_name} not found"
                    logger.error(msg)
                    tool_messages.append(
                        ToolMessage(content=msg, tool_call_id=tool_call["id"])
                    )

        state["messages"] = state["messages"] + tool_messages
        return state

    def _finalize_node(self, state: T) -> T:
        """
        Finalize the agent response
        """
        try:
            # Default finalization - can be overridden
            final_message = AIMessage(content=f"Completed successfully")
            state["messages"] = state["messages"] + [final_message]
            state = self._custom_finalization(state)
            
            return state
            
        except Exception as e:
            logger.error(f"Error in {self.agent_name} finalize node: {e}")
            error_message = AIMessage(content=f"Error finalizing {self.agent_name}: {str(e)}")
            state["messages"] = state["messages"] + [error_message]
            state["error"] = str(e)
            return state
    
    def _should_continue(self, state: T) -> str:
        if state.get("error"):
            return "end"
        
        last_message = state["messages"][-1]
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"
        if self._needs_finalization(state):
            return "finalize"        
        return "end"

    def _add_agent_context(self, messages: List[BaseMessage], state: T) -> List[BaseMessage]:
        """Add agent-specific context to messages - override if needed"""
        return messages
    
    def _update_agent_state(self, state: T, response: BaseMessage) -> T:
        """Update agent-specific state after LLM response - override if needed"""
        return state
    
    def _preprocess_tool_args(self, tool_args: Dict[str, Any], state: T) -> Dict[str, Any]:
        """Preprocess tool arguments before execution - override if needed"""
        return tool_args
    
    def _process_tool_result(self, state: T, tool_name: str, result: Any) -> T:
        """Process tool results and update state - override if needed"""
        return state
    
    def _custom_finalization(self, state: T) -> T:
        """Custom finalization logic - override if needed"""
        return state
    
    def _needs_finalization(self, state: T) -> bool:
        """Check if agent needs finalization step - override if needed"""
        return False

    def _extract_result(self, state: T) -> BaseAgentResult:
        """Extract a generic result object from the final state."""
        return BaseAgentResult(success=not bool(state.get("error")), error=state.get("error"))
    
    def process(self, query: str, conversation_id: str = "default", **kwargs) -> BaseAgentResult:
        """
        Process a query using the agent
        
        Args:
            query: User query
            conversation_id: Conversation ID for memory
            **kwargs: Additional arguments specific to the agent
            
        Returns:
            Agent-specific result object
        """
        try:
            logger.info(f"{self.agent_name} processing query: {query[:100]}...")
            
            # Create initial state
            initial_state = self._create_initial_state(query, conversation_id)
            
            # Add any additional kwargs to metadata
            if kwargs:
                metadata = dict(initial_state.get("metadata") or {})
                metadata.update(kwargs)
                initial_state["metadata"] = metadata
            
            config = {"configurable": {"thread_id": conversation_id}} if self.enable_memory else None
            
            final_state = self.graph.invoke(initial_state, config)
            
            return self._extract_result(final_state)
            
        except Exception as e:
            logger.error(f"Error processing query in {self.agent_name}: {e}")
            # Create error state and use _extract_result to maintain consistency
            error_state = self._create_initial_state(query, conversation_id)
            error_state["error"] = str(e)
            return self._extract_result(error_state)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about this agent"""
        return {
            "name": self.agent_name,
            "model": self.model_name,
            "temperature": self.temperature,
            "tools_count": len(self.tools),
            "memory_enabled": self.enable_memory,
            "agent_type": self.__class__.__name__
        }