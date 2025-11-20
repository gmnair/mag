"""Storage client abstraction supporting Cosmos DB and PostgreSQL."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from config import Config

logger = logging.getLogger(__name__)


class StorageClient(ABC):
    """Abstract base class for storage clients."""
    
    @abstractmethod
    def save_state(self, agent_id: str, state_id: str, state: Dict[str, Any]):
        """Save agent state."""
        pass
    
    @abstractmethod
    def get_state(self, agent_id: str, state_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent state."""
        pass
    
    @abstractmethod
    def save_task(self, agent_id: str, task_id: str, task_data: Dict[str, Any]):
        """Save task details."""
        pass
    
    @abstractmethod
    def get_task(self, agent_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve task details."""
        pass
    
    @abstractmethod
    def save_conversation(self, conversation_id: str, message: Dict[str, Any]):
        """Save conversation message."""
        pass
    
    @abstractmethod
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history."""
        pass
    
    @abstractmethod
    def save_transactions(self, case_id: str, transactions: List[Dict[str, Any]]):
        """Save transactions."""
        pass
    
    @abstractmethod
    def get_transactions(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieve transactions for a case."""
        pass


def create_storage_client() -> StorageClient:
    """Factory function to create appropriate storage client based on configuration."""
    # Check if PostgreSQL is configured
    if Config.POSTGRES_CONNECTION_STRING:
        logger.info("Using PostgreSQL as storage backend")
        from shared.postgres_client import PostgreSQLClient
        return PostgreSQLClient()
    
    # Check if Cosmos DB is configured
    elif Config.COSMOS_ENDPOINT and Config.COSMOS_KEY:
        logger.info("Using Cosmos DB as storage backend")
        from shared.cosmos_client import CosmosDBClient
        return CosmosDBClient()
    
    else:
        raise ValueError(
            "No storage backend configured. Please provide either:\n"
            "- POSTGRES_CONNECTION_STRING for PostgreSQL, or\n"
            "- COSMOS_ENDPOINT and COSMOS_KEY for Cosmos DB"
        )

