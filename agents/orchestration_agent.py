"""Orchestration Agent - Root agent using Deep Agent pattern."""
import logging
import uuid
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from agents.base_agent import BaseAgent
from shared.a2a_message import create_a2a_message, A2AMessageWrapper
from shared.state_manager import StateManager
from config import Config

logger = logging.getLogger(__name__)


class TransactionReviewRequest(BaseModel):
    """Request model for transaction review."""
    case_id: str
    file_path: str


class OrchestrationAgent(BaseAgent):
    """Orchestration agent using Deep Agent pattern and a2a-sdk types."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = FastAPI(title="Orchestration Agent API")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for A2A API."""
        
        @self.app.post("/api/v1/transaction-review")
        async def transaction_review(request: TransactionReviewRequest):
            """A2A API endpoint to trigger transaction review workflow."""
            try:
                conversation_id = str(uuid.uuid4())
                task_id = str(uuid.uuid4())
                
                # Create initial state
                state = self.state_manager.create_initial_state(
                    case_id=request.case_id,
                    file_path=request.file_path,
                    conversation_id=conversation_id
                )
                
                # Create task message for extractor agent using a2a-sdk types
                extractor_message = create_a2a_message(
                    message_id=task_id,
                    role="agent",
                    text=f"Extract transactions for case {request.case_id}",
                    context_id=conversation_id,
                    task_id=task_id
                )
                
                extractor_wrapper = A2AMessageWrapper(
                    message=extractor_message,
                    from_agent=self.agent_id,
                    to_agent=Config.EXTRACTOR_AGENT_ID,
                    payload={
                        "case_id": request.case_id,
                        "file_path": request.file_path,
                        "action": "extract_transactions"
                    }
                )
                
                # Send message to extractor agent
                await self.asb_client.send_message(extractor_wrapper, self.agent_id)
                
                logger.info(f"Workflow initiated for case {request.case_id}")
                
                return JSONResponse(content={
                    "status": "initiated",
                    "case_id": request.case_id,
                    "conversation_id": conversation_id,
                    "task_id": task_id
                })
                
            except Exception as e:
                logger.error(f"Error initiating workflow: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/v1/status/{case_id}")
        async def get_status(case_id: str):
            """Get status of transaction review workflow."""
            try:
                # Try to find state by case_id
                state = self.state_manager.load_state(self.agent_id, case_id)
                
                if not state:
                    raise HTTPException(status_code=404, detail="Case not found")
                
                return JSONResponse(content={
                    "case_id": case_id,
                    "status": state.get("status"),
                    "current_agent": state.get("current_agent"),
                    "summary": state.get("summary")
                })
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting status: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
    
    async def execute_task_from_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute orchestration task."""
        # Orchestration agent primarily handles API requests
        # Workflow coordination happens through message passing
        return {
            "status": "orchestrated",
            "message": "Workflow initiated"
        }
    
    def run_api_server(self):
        """Run the FastAPI server."""
        uvicorn.run(
            self.app,
            host=Config.A2A_API_HOST,
            port=Config.A2A_API_PORT,
            log_level="info"
        )
