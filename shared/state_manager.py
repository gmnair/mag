"""LangGraph state management for agent workflows."""
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from datetime import datetime
import uuid
from shared.storage_client import StorageClient
from shared.a2a_message import A2AMessage

logger = logging.getLogger(__name__)


class TransactionReviewState(TypedDict):
    """State for transaction review workflow."""
    case_id: str
    file_path: Optional[str]
    transactions: List[Dict[str, Any]]
    extracted_transactions: List[Dict[str, Any]]
    scap_results: Optional[Dict[str, Any]]
    summary: Optional[str]
    status: str
    error: Optional[str]
    conversation_id: str
    current_agent: str
    timestamp: str


class StateManager:
    """Manages state using LangGraph and Cosmos DB."""
    
    def __init__(self, storage_client: StorageClient):
        self.cosmos_client = storage_client  # Keep name for backward compatibility
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow."""
        workflow = StateGraph(TransactionReviewState)
        
        # Add nodes (agents will be called asynchronously via ASB)
        workflow.add_node("orchestration", self._orchestration_node)
        workflow.add_node("extraction", self._extraction_node)
        workflow.add_node("evaluation", self._evaluation_node)
        workflow.add_node("scap", self._scap_node)
        
        # Define edges
        workflow.set_entry_point("orchestration")
        workflow.add_edge("orchestration", "extraction")
        workflow.add_edge("extraction", "evaluation")
        workflow.add_edge("evaluation", "scap")
        workflow.add_edge("scap", END)
        
        return workflow.compile()
    
    def _orchestration_node(self, state: TransactionReviewState) -> TransactionReviewState:
        """Orchestration node - entry point."""
        state["current_agent"] = "orchestration"
        state["status"] = "orchestrating"
        return state
    
    def _extraction_node(self, state: TransactionReviewState) -> TransactionReviewState:
        """Extraction node - waits for extractor agent."""
        state["current_agent"] = "extraction"
        state["status"] = "extracting"
        return state
    
    def _evaluation_node(self, state: TransactionReviewState) -> TransactionReviewState:
        """Evaluation node - waits for evaluator agent."""
        state["current_agent"] = "evaluation"
        state["status"] = "evaluating"
        return state
    
    def _scap_node(self, state: TransactionReviewState) -> TransactionReviewState:
        """SCAP node - waits for SCAP agent."""
        state["current_agent"] = "scap"
        state["status"] = "scap_processing"
        return state
    
    def create_initial_state(
        self,
        case_id: str,
        file_path: str,
        conversation_id: Optional[str] = None
    ) -> TransactionReviewState:
        """Create initial state for workflow."""
        state: TransactionReviewState = {
            "case_id": case_id,
            "file_path": file_path,
            "transactions": [],
            "extracted_transactions": [],
            "scap_results": None,
            "summary": None,
            "status": "initialized",
            "error": None,
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "current_agent": "orchestration",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save initial state
        self.save_state("orchestration", state["conversation_id"], state)
        
        return state
    
    def save_state(self, agent_id: str, state_id: str, state: TransactionReviewState):
        """Save state to Cosmos DB."""
        self.cosmos_client.save_state(agent_id, state_id, dict(state))
    
    def load_state(self, agent_id: str, state_id: str) -> Optional[Dict[str, Any]]:
        """Load state from Cosmos DB."""
        state_dict = self.cosmos_client.get_state(agent_id, state_id)
        if state_dict:
            # Return as dict, can be used as TransactionReviewState
            return state_dict
        return None
    
    def update_state(
        self,
        agent_id: str,
        state_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update state with new values."""
        current_state = self.load_state(agent_id, state_id)
        if not current_state:
            raise ValueError(f"State not found: {state_id}")
        
        # Update state
        for key, value in updates.items():
            if key in TransactionReviewState.__annotations__:
                current_state[key] = value
        
        current_state["timestamp"] = datetime.utcnow().isoformat()
        
        # Save updated state
        self.save_state(agent_id, state_id, current_state)
        
        return current_state

