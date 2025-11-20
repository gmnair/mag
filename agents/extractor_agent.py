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
    
    async def execute_task_from_state(self, state: DeepAgentState) -> Dict[str, Any]:
        """Extract transactions from file and store in Cosmos DB."""
        try:
            context = state.get("context", {})
            payload = context.get("payload", {})
            case_id = payload.get("case_id") or state.get("case_id")
            file_path = payload.get("file_path")
            
            logger.info(f"Extracting transactions for case {case_id} from {file_path}")
            
            # Load state
            conversation_id = state.get("conversation_id") or case_id
            workflow_state = self.state_manager.load_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id
            )
            
            if not workflow_state:
                raise ValueError(f"State not found for case {case_id}")
            
            # Extract transactions from file
            transactions = await self._extract_transactions(file_path)
            
            # Store transactions in Cosmos DB
            self.cosmos_client.save_transactions(case_id, transactions)
            
            # Update workflow state
            self.state_manager.update_state(
                Config.ORCHESTRATION_AGENT_ID,
                conversation_id,
                {
                    "extracted_transactions": transactions,
                    "status": "extracted"
                }
            )
            
            # Send message to evaluator agent using a2a-sdk types
            task_id = state.get("task_id", "")
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
            
            await self.asb_client.send_message(evaluator_wrapper, self.agent_id)
            
            logger.info(f"Extracted {len(transactions)} transactions for case {case_id}")
            
            return {
                "status": "success",
                "transactions_extracted": len(transactions),
                "case_id": case_id
            }
            
        except Exception as e:
            logger.error(f"Error extracting transactions: {str(e)}", exc_info=True)
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
