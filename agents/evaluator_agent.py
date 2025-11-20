"""Evaluator Agent - Delegates to downstream agents using Deep Agent pattern."""
import logging
from typing import Dict, Any
from agents.base_agent import BaseAgent
from shared.deep_agent import DeepAgentState
from shared.a2a_message import create_a2a_message, A2AMessageWrapper
from shared.state_manager import StateManager
from config import Config

logger = logging.getLogger(__name__)


class EvaluatorAgent(BaseAgent):
    """Evaluator agent using Deep Agent pattern."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from a2a.server.events import QueueManager
        from a2a.server.tasks import DatabaseTaskStore
        self.queue_manager = QueueManager(
            queue_type="azure_service_bus",
            connection_string=Config.ASB_CONNECTION_STRING,
            topic_name=Config.ASB_TOPIC_NAME,
            subscription_name=Config.ASB_SUBSCRIPTION_NAME,
            agent_id=self.agent_id
        )
        self.task_store = DatabaseTaskStore(
            db_type="cosmos" if Config.COSMOS_ENDPOINT else "postgres",
            connection_string=Config.COSMOS_ENDPOINT if Config.COSMOS_ENDPOINT else Config.POSTGRES_CONNECTION_STRING,
            agent_id=self.agent_id
        )

    async def execute_task_from_state(self, state: DeepAgentState) -> Dict[str, Any]:
        """Delegate transaction evaluation to SCAP agent, with Langgraph flow."""
        task_id = state.get("task_id", "")
        # Start Langgraph flow: save initial state
        self.save_langgraph_state(task_id, state)
        try:
            context = state.get("context", {})
            payload = context.get("payload", {})
            case_id = payload.get("case_id") or state.get("case_id")
            transactions = payload.get("transactions", [])
            logger.info(f"Evaluating {len(transactions)} transactions for case {case_id}")
            conversation_id = state.get("conversation_id") or case_id
            workflow_state = self.state_manager.load_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id
            )
            if not workflow_state:
                raise ValueError(f"State not found for case {case_id}")
            # Save task to TaskStore
            self.task_store.save_task(
                self.agent_id,
                task_id,
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "status": "delegated",
                    "conversation_id": conversation_id
                }
            )
            scap_message = create_a2a_message(
                message_id=f"{task_id}_to_scap",
                role="agent",
                text="Transactions ready for SCAP validation",
                context_id=conversation_id,
                task_id=task_id
            )
            scap_wrapper = A2AMessageWrapper(
                message=scap_message,
                from_agent=self.agent_id,
                to_agent=Config.SCAP_AGENT_ID,
                payload={
                    "case_id": case_id,
                    "transactions": transactions,
                    "action": "validate_sensitive_countries"
                }
            )
            # Use QueueManager to send message
            await self.queue_manager.send_message(scap_wrapper)
            self.state_manager.update_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id,
                {
                    "status": "evaluating"
                }
            )
            logger.info(f"Delegated evaluation to SCAP agent for case {case_id}")
            result = {
                "status": "delegated",
                "delegated_to": Config.SCAP_AGENT_ID,
                "case_id": case_id
            }
            # End Langgraph flow: save final state
            self.save_langgraph_state(task_id, state)
            return result
        except Exception as e:
            logger.error(f"Error evaluating transactions: {str(e)}", exc_info=True)
            # End Langgraph flow: save error state
            self.save_langgraph_state(task_id, state)
            raise
