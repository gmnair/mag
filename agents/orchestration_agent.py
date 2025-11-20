from langgraph.graph import StateGraph, START, END

"""Orchestration Agent - Root agent using Deep Agent pattern."""
import logging
import uuid
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
try:
    from a2a.server import A2AServer
    from a2a.agent import AgentCard, AgentMetadata
    A2A_AVAILABLE = True
except ImportError:
    A2A_AVAILABLE = False
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
    class State:
        def __init__(self, messages=None):
            self.messages = messages or []

    """Orchestration agent using Deep Agent pattern and a2a-sdk types."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = FastAPI(title="Orchestration Agent API", docs_url="/docs", openapi_url="/openapi.json")
        self._setup_routes()
        # Setup A2A-compliant API using a2a-sdk
        from a2a.server.apps import A2AFastAPIApplication
        self.a2a_app = A2AFastAPIApplication()
        # Setup QueueManager for ASB
        from a2a.server.events import QueueManager
        from a2a.server.tasks import DatabaseTaskStore
        self.queue_manager = QueueManager(
            queue_type="azure_service_bus",
            connection_string=Config.ASB_CONNECTION_STRING,
            topic_name=Config.ASB_TOPIC_NAME,
            subscription_name=Config.ASB_SUBSCRIPTION_NAME,
            agent_id=self.agent_id
        )
        # Setup TaskStore for Cosmos/Postgres
        self.task_store = DatabaseTaskStore(
            db_type="cosmos" if Config.COSMOS_ENDPOINT else "postgres",
            connection_string=Config.COSMOS_ENDPOINT if Config.COSMOS_ENDPOINT else Config.POSTGRES_CONNECTION_STRING,
            agent_id=self.agent_id
        )
        self._setup_a2a_routes()
    def _setup_a2a_routes(self):
        """Setup A2A-compliant routes using a2a-sdk."""
        @self.a2a_app.method()
        async def transaction_review(case_id: str, file_path: str):
            """A2A API endpoint to trigger transaction review workflow."""
            try:
                conversation_id = str(uuid.uuid4())
                task_id = str(uuid.uuid4())
                state = self.state_manager.create_initial_state(
                    case_id=case_id,
                    file_path=file_path,
                    conversation_id=conversation_id
                )
                # Save initial task to TaskStore
                self.task_store.save_task(
                    self.agent_id,
                    task_id,
                    {
                        "task_id": task_id,
                        "case_id": case_id,
                        "file_path": file_path,
                        "status": "initiated",
                        "conversation_id": conversation_id
                    }
                )
                extractor_message = create_a2a_message(
                    message_id=task_id,
                    role="agent",
                    text=f"Extract transactions for case {case_id}",
                    context_id=conversation_id,
                    task_id=task_id
                )
                extractor_wrapper = A2AMessageWrapper(
                    message=extractor_message,
                    from_agent=self.agent_id,
                    to_agent=Config.EXTRACTOR_AGENT_ID,
                    payload={
                        "case_id": case_id,
                        "file_path": file_path,
                        "action": "extract_transactions"
                    }
                )
                # Use QueueManager to send message
                await self.queue_manager.send_message(extractor_wrapper)
                logger.info(f"A2A workflow initiated for case {case_id}")
                return {
                    "status": "initiated",
                    "case_id": case_id,
                    "conversation_id": conversation_id,
                    "task_id": task_id
                }
            except Exception as e:
                logger.error(f"Error initiating A2A workflow: {str(e)}", exc_info=True)
                return {"error": str(e)}
    
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
        """Execute orchestration task using Langgraph graph syntax and save state to CosmosDB after each node."""
        task_id = state.get("task_id", "")
        # Define Langgraph state
        graph_state = self.State(messages=state.get("messages", []))

        # Initialize graph builder
        graph_builder = StateGraph(self.State)

        # Define nodes
        def start_node(s: OrchestrationAgent.State):
            s.messages.append("Started orchestration")
            self.save_langgraph_state(task_id, {"node": "start", "messages": s.messages})
            return s

        def end_node(s: OrchestrationAgent.State):
            s.messages.append("Ended orchestration")
            self.save_langgraph_state(task_id, {"node": "end", "messages": s.messages})
            return s

        graph_builder.add_node("start", start_node)
        graph_builder.add_node("end", end_node)

        # Add edges
        graph_builder.add_edge(START, "start")
        graph_builder.add_edge("start", "end")
        graph_builder.add_edge("end", END)

        # Compile and execute graph
        graph = graph_builder.compile()
        graph_state.messages.append("Start message")
        final_state = graph.invoke(graph_state)
        self.save_langgraph_state(task_id, {"node": "END", "messages": final_state.messages})

        return {
            "status": "orchestrated",
            "message": "Langgraph flow executed",
            "langgraph_nodes": ["start", "end"],
            "langgraph_edges": [(START, "start"), ("start", "end"), ("end", END)],
            "final_messages": final_state.messages
        }
    
    def run_api_server(self, use_a2a=False):
        """Run the FastAPI server (Swagger) or A2A server if requested."""
        if use_a2a:
            uvicorn.run(
                self.a2a_app,
                host=Config.A2A_API_HOST,
                port=Config.A2A_API_PORT,
                log_level="info"
            )
        else:
            uvicorn.run(
                self.app,
                host=Config.A2A_API_HOST,
                port=Config.A2A_API_PORT,
                log_level="info"
            )
