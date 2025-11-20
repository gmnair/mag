"""Extractor Agent - Extracts transactions using Deep Agent pattern."""
import logging
import pandas as pd
import json
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from shared.deep_agent import DeepAgentState
from shared.a2a_message import create_a2a_message, A2AMessageWrapper
from shared.state_manager import StateManager
from config import Config

logger = logging.getLogger(__name__)


class ExtractorAgent(BaseAgent):
    """Extractor agent using Deep Agent pattern."""
    
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
        """Extract transactions from file and store in Cosmos DB, with Langgraph flow."""
        task_id = state.get("task_id", "")
        # Start Langgraph flow: save initial state
        self.save_langgraph_state(task_id, state)
        try:
            context = state.get("context", {})
            payload = context.get("payload", {})
            case_id = payload.get("case_id") or state.get("case_id")
            file_path = payload.get("file_path")
            logger.info(f"Extracting transactions for case {case_id} from {file_path}")
            conversation_id = state.get("conversation_id") or case_id
            workflow_state = self.state_manager.load_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id
            )
            if not workflow_state:
                raise ValueError(f"State not found for case {case_id}")
            transactions = await self._extract_transactions(file_path)
            self.cosmos_client.save_transactions(case_id, transactions)
            self.state_manager.update_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id,
                {
                    "extracted_transactions": transactions,
                    "status": "extracted"
                }
            )
            # Save task to TaskStore
            self.task_store.save_task(
                self.agent_id,
                task_id,
                {
                    "task_id": task_id,
                    "case_id": case_id,
                    "file_path": file_path,
                    "status": "extracted",
                    "conversation_id": conversation_id
                }
            )
            evaluator_message = create_a2a_message(
                message_id=f"{task_id}_to_evaluator",
                role="agent",
                text="Extracted transactions ready for evaluation",
                context_id=conversation_id,
                task_id=task_id
            )
            evaluator_wrapper = A2AMessageWrapper(
                message=evaluator_message,
                from_agent=self.agent_id,
                to_agent=Config.EVALUATOR_AGENT_ID,
                payload={
                    "case_id": case_id,
                    "transactions": transactions,
                    "action": "evaluate_transactions"
                }
            )
            # Use QueueManager to send message
            await self.queue_manager.send_message(evaluator_wrapper)
            logger.info(f"Extracted {len(transactions)} transactions for case {case_id}")
            result = {
                "status": "success",
                "transactions_extracted": len(transactions),
                "case_id": case_id
            }
            # End Langgraph flow: save final state
            self.save_langgraph_state(task_id, state)
            return result
        except Exception as e:
            logger.error(f"Error extracting transactions: {str(e)}", exc_info=True)
            # End Langgraph flow: save error state
            self.save_langgraph_state(task_id, state)
            raise
    
    async def _extract_transactions(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract transactions from file (supports CSV, JSON, Excel)."""
        try:
            # Determine file type and extract accordingly
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    else:
                        df = pd.DataFrame([data])
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Convert DataFrame to list of dictionaries
            transactions = df.to_dict('records')
            
            # Ensure each transaction has required fields
            for i, transaction in enumerate(transactions):
                if "transaction_id" not in transaction:
                    transaction["transaction_id"] = f"txn_{i+1}"
                if "id" not in transaction:
                    transaction["id"] = transaction["transaction_id"]
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
