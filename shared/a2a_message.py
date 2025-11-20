"""A2A Protocol message handling using a2a-sdk types."""
from typing import Dict, Any, Optional
from datetime import datetime
import json

try:
    from a2a.types import Message, Role, Part, MessageSendParams, MessageSendConfiguration
    from a2a.types import AgentCard, AgentMetadata as A2AAgentMetadata
    A2A_SDK_AVAILABLE = True
except ImportError:
    # Fallback if a2a-sdk is not available
    A2A_SDK_AVAILABLE = False
    Message = None
    Role = None
    Part = None
    MessageSendParams = None
    MessageSendConfiguration = None
    AgentCard = None
    A2AAgentMetadata = None


def create_a2a_message(
    message_id: str,
    role: str,
    text: str,
    context_id: Optional[str] = None,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """Create an A2A SDK Message."""
    if not A2A_SDK_AVAILABLE:
        raise ImportError("a2a-sdk is not installed. Please install it with: pip install a2a-sdk")
    
    role_enum = Role.USER if role.lower() == "user" else Role.AGENT
    
    parts = [Part(text=text)]
    if metadata:
        # Add metadata as additional parts if needed
        pass
    
    return Message(
        message_id=message_id,
        role=role_enum,
        parts=parts,
        context_id=context_id,
        task_id=task_id
    )


def create_message_send_params(
    message: Message,
    blocking: bool = True,
    history_length: int = 10
) -> MessageSendParams:
    """Create MessageSendParams for sending messages."""
    if not A2A_SDK_AVAILABLE:
        raise ImportError("a2a-sdk is not installed. Please install it with: pip install a2a-sdk")
    
    config = MessageSendConfiguration(
        blocking=blocking,
        history_length=history_length
    )
    
    return MessageSendParams(
        message=message,
        configuration=config
    )


def message_to_dict(message: Message) -> Dict[str, Any]:
    """Convert A2A Message to dictionary for serialization."""
    if not A2A_SDK_AVAILABLE:
        raise ImportError("a2a-sdk is not installed")
    
    return {
        "message_id": message.message_id,
        "role": message.role.value if hasattr(message.role, 'value') else str(message.role),
        "parts": [{"text": part.text} for part in message.parts] if message.parts else [],
        "context_id": message.context_id,
        "task_id": message.task_id
    }


def message_from_dict(data: Dict[str, Any]) -> Message:
    """Create A2A Message from dictionary."""
    if not A2A_SDK_AVAILABLE:
        raise ImportError("a2a-sdk is not installed")
    
    role = Role.USER if data.get("role", "").lower() == "user" else Role.AGENT
    parts = [Part(text=part.get("text", "")) for part in data.get("parts", [])]
    
    return Message(
        message_id=data.get("message_id", ""),
        role=role,
        parts=parts,
        context_id=data.get("context_id"),
        task_id=data.get("task_id")
    )


def message_to_json(message: Message) -> str:
    """Serialize A2A Message to JSON string."""
    return json.dumps(message_to_dict(message))


def message_from_json(json_str: str) -> Message:
    """Deserialize A2A Message from JSON string."""
    return message_from_dict(json.loads(json_str))


# Wrapper for backward compatibility with existing code
class A2AMessageWrapper:
    """Wrapper to adapt A2A SDK Message to our existing interface."""
    
    def __init__(self, message: Message, from_agent: str, to_agent: str, payload: Dict[str, Any]):
        self.message = message
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.payload = payload
        self.conversation_id = message.context_id
        self.correlation_id = message.task_id
        self.metadata = {
            "agent_id": from_agent,
            "agent_type": from_agent.split("-")[0] if "-" in from_agent else from_agent,
            "task_id": message.task_id or "",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "message": message_to_dict(self.message),
            "payload": self.payload,
            "metadata": self.metadata,
            "conversation_id": self.conversation_id,
            "correlation_id": self.correlation_id
        }
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str, from_agent: str, to_agent: str, payload: Dict[str, Any]):
        """Create from JSON."""
        data = json.loads(json_str)
        message = message_from_dict(data.get("message", {}))
        return cls(message, from_agent, to_agent, payload)
