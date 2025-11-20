"""Base agent class using Deep Agent pattern."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from shared.asb_client import ASBClient
from shared.storage_client import StorageClient
from shared.state_manager import StateManager
from shared.deep_agent import DeepAgent, DeepAgentState
from shared.a2a_message import create_a2a_message, message_to_dict, message_from_dict, A2AMessageWrapper

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    async def langgraph_flow(self, state_id: str, langgraph_state: Dict[str, Any]):
        """Example Langgraph flow: save and restore agent-isolated state."""
        # Save the current Langgraph state (isolated by agent_id)
        self.save_langgraph_state(state_id, langgraph_state)

        # Later, retrieve the Langgraph state for this agent and state_id
        restored_state = self.get_langgraph_state(state_id)
        if restored_state:
            # Continue processing with the retrieved state
            logger.info(f"{self.agent_id} restored Langgraph state for {state_id}")
            # ... agent-specific logic ...
        else:
            logger.warning(f"{self.agent_id} could not find Langgraph state for {state_id}")
    """Base class for all agents using Deep Agent pattern."""
    
    def __init__(
        self,
        agent_id: str,
        asb_client: ASBClient,
        cosmos_client: StorageClient,  # Can be CosmosDBClient or PostgreSQLClient
        state_manager: StateManager,
        llm_model: str = None
    ):
        self.agent_id = agent_id
        self.asb_client = asb_client
        self.cosmos_client = cosmos_client
        self.state_manager = state_manager
        self.running = False
        
        # Initialize Deep Agent
        self.deep_agent = DeepAgent(
            agent_id=agent_id,
            cosmos_client=cosmos_client,
            asb_client=asb_client,
            llm_model=llm_model
        )
        
        # Override execute node in deep agent
        self.deep_agent._execute_node = self._deep_execute_node
    
    async def _deep_execute_node(self, state: DeepAgentState) -> DeepAgentState:
        """Execute node that calls the agent's specific task execution."""
        logger.info(f"{self.agent_id} - Executing plan in Deep Agent cycle...")
        
        try:
            # Extract task information from state
            task_id = state.get("task_id", "")
            case_id = state.get("case_id")
            context = state.get("context", {})
            
            # Get the original message from context if available
            message_data = context.get("message_data", {})
            
            # Execute the specific agent task
            result = await self.execute_task_from_state(state)
            
            # Update execution results
            state["execution_results"] = [
                {
                    "status": "success",
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            logger.info(f"{self.agent_id} - Execution completed successfully")
            
        except Exception as e:
            logger.error(f"{self.agent_id} - Execution error: {str(e)}", exc_info=True)
            state["execution_results"] = [
                {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        
        return state
    
    @abstractmethod
    async def execute_task_from_state(self, state: DeepAgentState) -> Dict[str, Any]:
        """Execute the agent's specific task. Must be implemented by subclasses."""
        pass
    
    async def handle_message(self, message_wrapper: A2AMessageWrapper):
        """Handle incoming A2A message using Deep Agent pattern."""
        try:
            logger.info(f"{self.agent_id} received message from {message_wrapper.from_agent}")
            
            # Extract information from message
            message = message_wrapper.message
            payload = message_wrapper.payload
            conversation_id = message.context_id or message.task_id
            task_id = message.task_id or ""
            case_id = payload.get("case_id") or message_wrapper.metadata.get("case_id")
            
            # Save conversation message
            self.cosmos_client.save_conversation(
                conversation_id,
                {
                    "id": task_id,
                    "from_agent": message_wrapper.from_agent,
                    "to_agent": message_wrapper.to_agent,
                    "message": message_to_dict(message),
                    "payload": payload,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Save task details
            self.cosmos_client.save_task(
                self.agent_id,
                task_id,
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "message": message_wrapper.to_dict(),
                    "status": "processing",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Prepare initial state for Deep Agent cycle
            initial_state = {
                "task_id": task_id,
                "case_id": case_id,
                "conversation_id": conversation_id,
                "goals": self._extract_goals(payload),
                "context": {
                    "message_data": message_wrapper.to_dict(),
                    "payload": payload,
                    "from_agent": message_wrapper.from_agent
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Run Deep Agent cycle (sense-perceive-plan-learn)
            deep_state = await self.deep_agent.run_cycle(initial_state)
            
            # Extract result from execution
            execution_results = deep_state.get("execution_results", [])
            result = execution_results[0].get("result", {}) if execution_results else {}
            
            # Update task status
            self.cosmos_client.save_task(
                self.agent_id,
                task_id,
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "message": message_wrapper.to_dict(),
                    "result": result,
                    "deep_agent_state": {
                        "perception": deep_state.get("perception"),
                        "plan": deep_state.get("plan"),
                        "learning": deep_state.get("learning")
                    },
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            # Send response if needed
            if message_wrapper.from_agent:
                await self._send_response(message_wrapper, result, conversation_id, task_id, case_id)
            
            logger.info(f"{self.agent_id} - Message handling completed")
            
        except Exception as e:
            logger.error(f"{self.agent_id} error handling message: {str(e)}", exc_info=True)
            
            # Send error response
            if message_wrapper.from_agent:
                await self._send_error_response(message_wrapper, str(e), conversation_id, task_id, case_id)
    
    def _extract_goals(self, payload: Dict[str, Any]) -> List[str]:
        """Extract goals from payload."""
        action = payload.get("action", "")
        goals = []
        
        if action:
            goals.append(f"Execute action: {action}")
        
        if payload.get("case_id"):
            goals.append(f"Process case: {payload.get('case_id')}")
        
        return goals if goals else ["Complete assigned task"]
    
    async def _send_response(
        self,
        original_message: A2AMessageWrapper,
        result: Dict[str, Any],
        conversation_id: str,
        task_id: str,
        case_id: Optional[str]
    ):
        """Send response message back to originating agent."""
        try:
            from shared.a2a_message import create_a2a_message, A2AMessageWrapper
            
            response_message = create_a2a_message(
                message_id=f"{task_id}_response",
                role="agent",
                text=f"Task completed: {result.get('status', 'success')}",
                context_id=conversation_id,
                task_id=task_id
            )
            
            response_wrapper = A2AMessageWrapper(
                message=response_message,
                from_agent=self.agent_id,
                to_agent=original_message.from_agent,
                payload=result
            )
            
            await self.asb_client.send_message(response_wrapper, self.agent_id)
            logger.info(f"{self.agent_id} sent response to {original_message.from_agent}")
            
        except Exception as e:
            logger.error(f"Error sending response: {str(e)}")
    
    async def _send_error_response(
        self,
        original_message: A2AMessageWrapper,
        error: str,
        conversation_id: str,
        task_id: str,
        case_id: Optional[str]
    ):
        """Send error response back to originating agent."""
        try:
            from shared.a2a_message import create_a2a_message, A2AMessageWrapper
            
            error_message = create_a2a_message(
                message_id=f"{task_id}_error",
                role="agent",
                text=f"Error: {error}",
                context_id=conversation_id,
                task_id=task_id
            )
            
            error_wrapper = A2AMessageWrapper(
                message=error_message,
                from_agent=self.agent_id,
                to_agent=original_message.from_agent,
                payload={"error": error, "status": "failed"}
            )
            
            await self.asb_client.send_message(error_wrapper, self.agent_id)
            logger.info(f"{self.agent_id} sent error response to {original_message.from_agent}")
            
        except Exception as e:
            logger.error(f"Error sending error response: {str(e)}")
    
    async def start(self):
        """Start the agent message listener using shared subscription."""
        self.running = True
        logger.info(f"{self.agent_id} starting with shared subscription...")
        
        # Ensure shared subscription exists (agent_id is optional now)
        await self.asb_client.ensure_subscription_exists()
        
        # Start receiving messages from shared subscription
        while self.running:
            try:
                await self.asb_client.receive_messages(
                    self.agent_id,
                    self._handle_message_wrapper,
                    max_wait_time=5
                )
            except Exception as e:
                logger.error(f"{self.agent_id} error in message loop: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _handle_message_wrapper(self, message_data: Any):
        """Wrapper to convert ASB message to A2A message wrapper."""
        try:
            import json
            from shared.a2a_message import message_from_dict, A2AMessageWrapper
            
            # Parse message from ASB
            if hasattr(message_data, 'body'):
                message_body = message_data.body.decode('utf-8')
                data = json.loads(message_body)
            else:
                data = message_data
            
            # Extract message components
            message_dict = data.get("message", {})
            from_agent = data.get("from_agent", "")
            to_agent = data.get("to_agent", "")
            payload = data.get("payload", {})
            
            # Create A2A message
            a2a_message = message_from_dict(message_dict)
            
            # Create wrapper
            message_wrapper = A2AMessageWrapper(
                message=a2a_message,
                from_agent=from_agent,
                to_agent=to_agent,
                payload=payload
            )
            
            await self.handle_message(message_wrapper)
            
        except Exception as e:
            logger.error(f"Error parsing message: {str(e)}", exc_info=True)
    
    async def stop(self):
        """Stop the agent message listener."""
        self.running = False
        logger.info(f"{self.agent_id} stopping...")
    
    # When saving Langgraph state, always use agent_id as part of the key
    # This ensures agents only fetch their own state
    def save_langgraph_state(self, state_id: str, state: Dict[str, Any]):
        self.cosmos_client.save_state(self.agent_id, state_id, state)

    def get_langgraph_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        return self.cosmos_client.get_state(self.agent_id, state_id)

    # Example usage in agent logic:
    # self.save_langgraph_state(task_id, langgraph_state)
    # state = self.get_langgraph_state(task_id)
    # This pattern works for both CosmosDB and PostgreSQL backends
