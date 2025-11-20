"""Azure Cosmos DB client for state, task, and conversation storage."""
import logging
from typing import Dict, Any, Optional, List
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from config import Config
from shared.storage_client import StorageClient
from shared.conversation_store import ConversationStore
import json
import uuid

logger = logging.getLogger(__name__)


class CosmosDBClient(StorageClient):
    """Cosmos DB client for storing agent states, tasks, and conversations."""
    
    def __init__(
        self,
        endpoint: str = None,
        key: str = None,
        database_name: str = None
    ):
        self.endpoint = endpoint or Config.COSMOS_ENDPOINT
        self.key = key or Config.COSMOS_KEY
        self.database_name = database_name or Config.COSMOS_DATABASE_NAME
        
        self.client = CosmosClient(self.endpoint, self.key)
        self.database = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database and containers."""
        try:
            # Create database if it doesn't exist
            try:
                self.database = self.client.get_database_client(self.database_name)
                self.database.read()
            except CosmosResourceNotFoundError:
                self.database = self.client.create_database(self.database_name)
            
            # Create containers if they don't exist
            containers = [
                Config.COSMOS_STATE_CONTAINER,
                Config.COSMOS_TASK_CONTAINER,
                Config.COSMOS_CONVERSATION_CONTAINER,
                Config.COSMOS_TRANSACTION_CONTAINER
            ]
            
            for container_name in containers:
                try:
                    container = self.database.get_container_client(container_name)
                    container.read()
                except CosmosResourceNotFoundError:
                    self.database.create_container(
                        id=container_name,
                        partition_key=PartitionKey(path="/id")
                    )
                    logger.info(f"Created container: {container_name}")
                    
        except Exception as e:
            logger.error(f"Error initializing Cosmos DB: {str(e)}")
            raise
    
    def save_state(self, agent_id: str, state_id: str, state: Dict[str, Any]):
        """Save agent state to Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_STATE_CONTAINER)
            
            state_doc = {
                "id": f"{agent_id}_{state_id}",
                "agent_id": agent_id,
                "state_id": state_id,
                "state": state,
                "timestamp": state.get("timestamp", "")
            }
            
            container.upsert_item(state_doc)
            logger.info(f"Saved state for {agent_id}: {state_id}")
            
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}")
            raise
    
    def get_state(self, agent_id: str, state_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent state from Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_STATE_CONTAINER)
            
            doc_id = f"{agent_id}_{state_id}"
            state_doc = container.read_item(item=doc_id, partition_key=doc_id)
            
            return state_doc.get("state")
            
        except CosmosResourceNotFoundError:
            logger.warning(f"State not found for {agent_id}: {state_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving state: {str(e)}")
            raise
    
    def save_task(self, agent_id: str, task_id: str, task_data: Dict[str, Any]):
        """Save task details to Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_TASK_CONTAINER)
            
            task_doc = {
                "id": f"{agent_id}_{task_id}",
                "agent_id": agent_id,
                "task_id": task_id,
                "task_data": task_data,
                "timestamp": task_data.get("timestamp", "")
            }
            
            container.upsert_item(task_doc)
            logger.info(f"Saved task for {agent_id}: {task_id}")
            
        except Exception as e:
            logger.error(f"Error saving task: {str(e)}")
            raise
    
    def get_task(self, agent_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task details from Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_TASK_CONTAINER)
            
            doc_id = f"{agent_id}_{task_id}"
            task_doc = container.read_item(item=doc_id, partition_key=doc_id)
            
            return task_doc.get("task_data")
            
        except CosmosResourceNotFoundError:
            logger.warning(f"Task not found for {agent_id}: {task_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving task: {str(e)}")
            raise
    
    def save_conversation(self, conversation_id: str, message: Dict[str, Any]):
        """Save conversation message to Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_CONVERSATION_CONTAINER)
            
            # Use message ID or timestamp as unique identifier
            message_id = message.get("id", f"{conversation_id}_{message.get('timestamp', '')}")
            
            conv_doc = {
                "id": message_id,
                "conversation_id": conversation_id,
                "message": message,
                "timestamp": message.get("timestamp", "")
            }
            
            container.upsert_item(conv_doc)
            logger.debug(f"Saved conversation message: {conversation_id}")
            
        except Exception as e:
            logger.error(f"Error saving conversation: {str(e)}")
            raise
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history from Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_CONVERSATION_CONTAINER)
            
            query = f"SELECT * FROM c WHERE c.conversation_id = '{conversation_id}' ORDER BY c.timestamp ASC"
            
            items = container.query_items(query=query, enable_cross_partition_query=True)
            messages = [item.get("message") for item in items]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []
    
    def save_transactions(self, case_id: str, transactions: List[Dict[str, Any]]):
        """Save transactions to Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_TRANSACTION_CONTAINER)
            
            for transaction in transactions:
                transaction_doc = {
                    "id": transaction.get("transaction_id", f"{case_id}_{transaction.get('id', '')}"),
                    "case_id": case_id,
                    "transaction": transaction,
                    "timestamp": transaction.get("timestamp", "")
                }
                
                container.upsert_item(transaction_doc)
            
            logger.info(f"Saved {len(transactions)} transactions for case: {case_id}")
            
        except Exception as e:
            logger.error(f"Error saving transactions: {str(e)}")
            raise
    
    def get_transactions(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve transactions for a case from Cosmos DB."""
        try:
            container = self.database.get_container_client(Config.COSMOS_TRANSACTION_CONTAINER)
            
            query = f"SELECT * FROM c WHERE c.case_id = '{case_id}' ORDER BY c.timestamp ASC"
            
            items = container.query_items(query=query, enable_cross_partition_query=True)
            transactions = [item.get("transaction") for item in items]
            
            return transactions
            
        except Exception as e:
            logger.error(f"Error retrieving transactions: {str(e)}")
            return []
    

class CosmosDBConversationStore(ConversationStore):
    def __init__(self):
        self.client = CosmosClient(Config.COSMOS_ENDPOINT, Config.COSMOS_KEY)
        self.database_name = getattr(Config, "COSMOS_DATABASE", "conversations")
        self.container_name = getattr(Config, "COSMOS_CONTAINER", "messages")
        self.database = self.client.create_database_if_not_exists(self.database_name)
        self.container = self.database.create_container_if_not_exists(
            id=self.container_name,
            partition_key=PartitionKey(path="/context_id"),
            offer_throughput=400
        )

    def save_conversation(self, context_id: str, user: str, message: Dict[str, Any]):
        doc = {
            "id": str(uuid.uuid4()),
            "context_id": context_id,
            "user": user,
            "message": message
        }
        self.container.upsert_item(doc)
        logger.info(f"Saved message for context {context_id}, user {user} in Cosmos DB")

    def get_conversation(self, context_id: str, user: Optional[str] = None) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM c WHERE c.context_id=@context_id"
        params = [{"name": "@context_id", "value": context_id}]
        if user:
            query += " AND c.user=@user"
            params.append({"name": "@user", "value": user})
        items = list(self.container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True
        ))
        logger.info(f"Retrieved {len(items)} messages for context {context_id}, user {user} from Cosmos DB")
        return [item["message"] for item in items]

    def summarize_conversation(self, context_id: str, user: Optional[str] = None) -> str:
        messages = self.get_conversation(context_id, user)
        summary = f"Summary for context {context_id}, user {user}: {len(messages)} messages."
        # Optionally, use LLM or custom logic for richer summary
        logger.info(f"Summarized conversation for context {context_id}, user {user}")
        return summary

