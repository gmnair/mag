"""Conversation store abstraction supporting Cosmos DB and PostgreSQL."""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from config import Config

logger = logging.getLogger(__name__)

class ConversationStore(ABC):
    """Abstract base class for conversation stores."""
    @abstractmethod
    def save_conversation(self, context_id: str, user: str, message: Dict[str, Any]):
        """Save a message for a conversation context and user."""
        pass

    @abstractmethod
    def get_conversation(self, context_id: str, user: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all messages for a conversation context (optionally filtered by user)."""
        pass

    @abstractmethod
    def summarize_conversation(self, context_id: str, user: Optional[str] = None) -> str:
        """Summarize the conversation for a context (optionally filtered by user)."""
        pass


def create_conversation_store() -> ConversationStore:
    """Factory function to create appropriate conversation store based on configuration."""
    if Config.POSTGRES_CONNECTION_STRING:
        logger.info("Using PostgreSQL as conversation store backend")
        from shared.postgres_client import PostgreSQLConversationStore
        return PostgreSQLConversationStore()
    elif Config.COSMOS_ENDPOINT and Config.COSMOS_KEY:
        logger.info("Using Cosmos DB as conversation store backend")
        from shared.cosmos_client import CosmosDBConversationStore
        return CosmosDBConversationStore()
    else:
        raise ValueError(
            "No conversation store backend configured. Please provide either:\n"
            "- POSTGRES_CONNECTION_STRING for PostgreSQL, or\n"
            "- COSMOS_ENDPOINT and COSMOS_KEY for Cosmos DB"
        )
