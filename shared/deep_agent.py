"""Deep Agent pattern implementation with sense-perceive-plan-learn cycle."""
import logging
import json
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from shared.storage_client import StorageClient
from shared.asb_client import ASBClient
from config import Config
from prompts import get_template_manager
from llm_config import create_llm

logger = logging.getLogger(__name__)


class DeepAgentState(TypedDict):
    """State for Deep Agent cycle."""
    agent_id: str
    context: Dict[str, Any]
    goals: List[str]
    discovered_tools: List[Dict[str, Any]]
    discovered_agents: List[Dict[str, Any]]
    perception: Dict[str, Any]
    plan: List[Dict[str, Any]]
    execution_results: List[Dict[str, Any]]
    learning: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    task_id: str
    case_id: Optional[str]
    timestamp: str


class DeepAgent:
    """Base class for Deep Agent pattern with sense-perceive-plan-learn cycle."""
    
    def __init__(
        self,
        agent_id: str,
        cosmos_client: StorageClient,
        asb_client: ASBClient,
        llm_model: str = None
    ):
        self.agent_id = agent_id
        self.cosmos_client = cosmos_client
        self.asb_client = asb_client
        
        # Create LLM using factory from configuration
        try:
            # If llm_model is provided, use it as override
            override_params = {}
            if llm_model:
                override_params["model"] = llm_model
            
            self.llm = create_llm(**override_params)
            if self.llm:
                logger.info(f"{self.agent_id} - LLM initialized using configured provider")
            else:
                logger.warning(f"{self.agent_id} - LLM not available (no API key or provider not configured)")
        except Exception as e:
            logger.error(f"{self.agent_id} - Error initializing LLM: {str(e)}")
            self.llm = None
        
        # Build LangGraph workflow
        self.graph = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for sense-perceive-plan-learn cycle."""
        workflow = StateGraph(DeepAgentState)
        
        # Add nodes
        workflow.add_node("sense", self._sense_node)
        workflow.add_node("perceive", self._perceive_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("learn", self._learn_node)
        
        # Define edges
        workflow.set_entry_point("sense")
        workflow.add_edge("sense", "perceive")
        workflow.add_edge("perceive", "plan")
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "learn")
        workflow.add_edge("learn", END)
        
        return workflow.compile()
    
    async def _sense_node(self, state: DeepAgentState) -> DeepAgentState:
        """Sense: Discover tools, agents, context, and goals."""
        logger.info(f"{self.agent_id} - Sensing environment...")
        
        # Discover available tools
        tools = await self._discover_tools(state)
        
        # Discover available agents
        agents = await self._discover_agents(state)
        
        # Retrieve context from Cosmos DB
        context = await self._retrieve_context(state)
        
        # Extract goals from state or context
        goals = state.get("goals", [])
        if not goals and context:
            goals = context.get("goals", [])
        
        state["discovered_tools"] = tools
        state["discovered_agents"] = agents
        state["context"] = context or state.get("context", {})
        state["goals"] = goals
        
        logger.info(f"{self.agent_id} - Discovered {len(tools)} tools, {len(agents)} agents")
        
        return state
    
    async def _perceive_node(self, state: DeepAgentState) -> DeepAgentState:
        """Perceive: Understand the environment based on goals using LLM."""
        logger.info(f"{self.agent_id} - Perceiving environment...")
        
        if not self.llm:
            # Fallback without LLM
            state["perception"] = {
                "understanding": "Basic perception without LLM",
                "relevant_context": state.get("context", {}),
                "priority": "medium"
            }
            return state
        
        # Use LLM to understand the situation
        context_str = self._format_context_for_llm(state)
        goals = state.get("goals", [])
        tool_count = len(state.get("discovered_tools", []))
        agent_count = len(state.get("discovered_agents", []))
        
        # Use prompt template
        template_manager = get_template_manager()
        prompt = template_manager.render_template(
            "deep_agent_perception",
            context=context_str,
            goals=goals,
            tool_count=tool_count,
            agent_count=agent_count
        )
        
        # Get system message if available
        system_message = template_manager.get_system_message("deep_agent_perception")
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = await self.llm.ainvoke(messages)
            perception_text = response.content
            
            # Parse LLM response (simplified - in production use structured output)
            state["perception"] = {
                "understanding": perception_text,
                "relevant_context": state.get("context", {}),
                "priority": "medium",
                "raw_response": perception_text
            }
        except Exception as e:
            logger.error(f"Error in LLM perception: {str(e)}")
            state["perception"] = {
                "understanding": "Error in perception",
                "relevant_context": state.get("context", {}),
                "priority": "medium"
            }
        
        return state
    
    async def _plan_node(self, state: DeepAgentState) -> DeepAgentState:
        """Plan: Create execution plan using LLM and LangGraph."""
        logger.info(f"{self.agent_id} - Planning execution...")
        
        if not self.llm:
            # Fallback plan
            state["plan"] = [{"action": "execute_task", "description": "Execute assigned task"}]
            return state
        
        # Use LLM to create a plan
        perception = state.get("perception", {})
        goals = state.get("goals", [])
        tools = state.get("discovered_tools", [])
        agents = state.get("discovered_agents", [])
        
        # Use prompt template
        template_manager = get_template_manager()
        prompt = template_manager.render_template(
            "deep_agent_planning",
            perception=perception.get('understanding', 'No perception available'),
            goals=goals,
            tools=tools,
            agents=agents
        )
        
        # Get system message if available
        system_message = template_manager.get_system_message("deep_agent_planning")
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = await self.llm.ainvoke(messages)
            plan_text = response.content
            
            # Parse plan (simplified - in production use structured output)
            # For now, create a basic plan structure
            state["plan"] = [
                {
                    "step_number": 1,
                    "action": "execute_task",
                    "tool_or_agent": "self",
                    "description": plan_text[:200],
                    "expected_outcome": "Task completion"
                }
            ]
            
            logger.info(f"{self.agent_id} - Created plan with {len(state['plan'])} steps")
        except Exception as e:
            logger.error(f"Error in LLM planning: {str(e)}")
            state["plan"] = [{"action": "execute_task", "description": "Fallback plan"}]
        
        return state
    
    async def _execute_node(self, state: DeepAgentState) -> DeepAgentState:
        """Execute: Execute the plan (to be implemented by subclasses)."""
        logger.info(f"{self.agent_id} - Executing plan...")
        
        # This will be overridden by specific agents
        state["execution_results"] = [{"status": "pending", "message": "Execution not implemented"}]
        
        return state
    
    async def _learn_node(self, state: DeepAgentState) -> DeepAgentState:
        """Learn: Analyze outcomes and update context history."""
        logger.info(f"{self.agent_id} - Learning from outcomes...")
        
        execution_results = state.get("execution_results", [])
        plan = state.get("plan", [])
        
        if not self.llm:
            # Fallback learning
            state["learning"] = {
                "outcome": "completed",
                "lessons": ["Task executed"],
                "context_updates": {}
            }
            return state
        
        # Use LLM to analyze outcomes
        template_manager = get_template_manager()
        prompt = template_manager.render_template(
            "deep_agent_learning",
            plan=plan,
            execution_results=execution_results
        )
        
        # Get system message if available
        system_message = template_manager.get_system_message("deep_agent_learning")
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        try:
            response = await self.llm.ainvoke(messages)
            learning_text = response.content
            
            state["learning"] = {
                "outcome": "completed",
                "lessons": [learning_text[:200]],
                "context_updates": {},
                "raw_response": learning_text
            }
            
            # Save learning to context history
            await self._save_context_history(state)
            
        except Exception as e:
            logger.error(f"Error in LLM learning: {str(e)}")
            state["learning"] = {
                "outcome": "completed",
                "lessons": ["Execution completed"],
                "context_updates": {}
            }
        
        return state
    
    async def _discover_tools(self, state: DeepAgentState) -> List[Dict[str, Any]]:
        """Discover available tools for this agent."""
        tools = []
        
        # Base tools (storage and messaging)
        tools.extend([
            {"name": "cosmos_db", "description": "Azure Cosmos DB access", "type": "storage"},
            {"name": "service_bus", "description": "Azure Service Bus messaging", "type": "messaging"}
        ])
        
        # Discover MCP servers as tools
        try:
            from discovery import get_discovery_service
            
            discovery_service = get_discovery_service()
            mcp_servers = discovery_service.discover_mcp_servers()
            
            for server in mcp_servers:
                tools.append({
                    "name": server.get("id"),
                    "description": server.get("metadata", {}).get("description", server.get("name", "")),
                    "type": "mcp_server",
                    "mcp_type": server.get("type"),
                    "capabilities": server.get("capabilities", []),
                    "endpoint": server.get("endpoint"),
                    "transport": server.get("transport")
                })
            
            logger.info(f"{self.agent_id} - Discovered {len(mcp_servers)} MCP servers")
            
        except Exception as e:
            logger.warning(f"Error discovering MCP servers: {str(e)}")
        
        return tools
    
    async def _discover_agents(self, state: DeepAgentState) -> List[Dict[str, Any]]:
        """Discover available agents in the system."""
        from discovery import get_discovery_service
        
        discovery_service = get_discovery_service()
        agents = discovery_service.discover_agents()
        
        # Format for Deep Agent state
        formatted_agents = []
        for agent in agents:
            formatted_agents.append({
                "id": agent.get("id"),
                "name": agent.get("name", agent.get("id")),
                "type": agent.get("type", "unknown"),
                "capabilities": ", ".join(agent.get("capabilities", [])),
                "status": agent.get("status", "unknown"),
                "metadata": agent.get("metadata", {})
            })
        
        logger.info(f"{self.agent_id} - Discovered {len(formatted_agents)} agents")
        return formatted_agents
    
    async def _retrieve_context(self, state: DeepAgentState) -> Optional[Dict[str, Any]]:
        """Retrieve context from Cosmos DB."""
        task_id = state.get("task_id")
        case_id = state.get("case_id")
        conversation_id = state.get("conversation_id")
        
        if conversation_id:
            # Retrieve conversation history
            history = self.cosmos_client.get_conversation_history(conversation_id)
            if history:
                return {
                    "conversation_history": history,
                    "last_state": history[-1] if history else {}
                }
        
        if task_id:
            # Retrieve task context
            task_data = self.cosmos_client.get_task(self.agent_id, task_id)
            if task_data:
                return {"task_context": task_data}
        
        return None
    
    async def _save_context_history(self, state: DeepAgentState):
        """Save context history to Cosmos DB."""
        conversation_id = state.get("conversation_id") or state.get("task_id")
        if not conversation_id:
            return
        
        learning = state.get("learning", {})
        execution_results = state.get("execution_results", [])
        
        context_entry = {
            "id": f"{conversation_id}_{state.get('timestamp', '')}",
            "agent_id": self.agent_id,
            "task_id": state.get("task_id"),
            "case_id": state.get("case_id"),
            "learning": learning,
            "execution_results": execution_results,
            "plan": state.get("plan", []),
            "timestamp": state.get("timestamp")
        }
        
        self.cosmos_client.save_conversation(conversation_id, context_entry)
        logger.info(f"{self.agent_id} - Saved context history for {conversation_id}")
    
    def _format_context_for_llm(self, state: DeepAgentState) -> str:
        """Format context for LLM input."""
        context = state.get("context", {})
        if isinstance(context, dict):
            return json.dumps(context, indent=2)
        return str(context)
    
    async def run_cycle(self, initial_state: Dict[str, Any]) -> DeepAgentState:
        """Run the complete sense-perceive-plan-learn cycle."""
        # Convert initial state to DeepAgentState
        deep_state: DeepAgentState = {
            "agent_id": self.agent_id,
            "context": initial_state.get("context", {}),
            "goals": initial_state.get("goals", []),
            "discovered_tools": [],
            "discovered_agents": [],
            "perception": {},
            "plan": [],
            "execution_results": [],
            "learning": {},
            "conversation_history": [],
            "task_id": initial_state.get("task_id", ""),
            "case_id": initial_state.get("case_id"),
            "timestamp": initial_state.get("timestamp", "")
        }
        
        # Run the workflow
        result = await self.graph.ainvoke(deep_state)
        
        return result

