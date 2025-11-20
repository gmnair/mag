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
    
    async def execute_task_from_state(self, state: DeepAgentState) -> Dict[str, Any]:
        """Delegate transaction evaluation to SCAP agent."""
        try:
            context = state.get("context", {})
            payload = context.get("payload", {})
            case_id = payload.get("case_id") or state.get("case_id")
            transactions = payload.get("transactions", [])
            
            logger.info(f"Evaluating {len(transactions)} transactions for case {case_id}")
            
            # Load workflow state
            conversation_id = state.get("conversation_id") or case_id
            workflow_state = self.state_manager.load_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id
            )
            
            if not workflow_state:
                raise ValueError(f"State not found for case {case_id}")
            
            # Delegate to SCAP agent using a2a-sdk types
            task_id = state.get("task_id", "")
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
            
            await self.asb_client.send_message(scap_wrapper, self.agent_id)
            
            # Update workflow state
            self.state_manager.update_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id,
                {
                    "status": "evaluating"
                }
            )
            
            logger.info(f"Delegated evaluation to SCAP agent for case {case_id}")
            
            return {
                "status": "delegated",
                "delegated_to": Config.SCAP_AGENT_ID,
                "case_id": case_id
            }
            
        except Exception as e:
            logger.error(f"Error evaluating transactions: {str(e)}", exc_info=True)
            raise
