"""Main entry point for running agents."""
import asyncio
import logging
import sys
from config import Config
from shared.asb_client import ASBClient
from shared.storage_client import create_storage_client
from shared.state_manager import StateManager
from agents.orchestration_agent import OrchestrationAgent
from agents.extractor_agent import ExtractorAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.scap_agent import SCAPAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_agent(agent_id: str, agent_class, llm_model: str = None):
    """Create and initialize an agent."""
    asb_client = ASBClient()
    storage_client = create_storage_client()
    state_manager = StateManager(storage_client)
    
    return agent_class(
        agent_id=agent_id,
        asb_client=asb_client,
        cosmos_client=storage_client,  # Keep parameter name for backward compatibility
        state_manager=state_manager,
        llm_model=llm_model
    )


async def run_agent(agent_id: str, agent_class, llm_model: str = None):
    """Run an agent in async mode."""
    agent = create_agent(agent_id, agent_class, llm_model)
    logger.info(f"Starting {agent_id}...")
    await agent.start()


def run_orchestration_agent():
    """Run orchestration agent with API server."""
    agent = create_agent(Config.ORCHESTRATION_AGENT_ID, OrchestrationAgent, Config.OPENAI_MODEL)
    logger.info("Starting Orchestration Agent with API server...")
    agent.run_api_server()


async def main():
    """Main function to run agents."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <agent_name>")
        print("Available agents: orchestration, extractor, evaluator, scap")
        sys.exit(1)
    
    agent_name = sys.argv[1].lower()
    
    agent_map = {
        "orchestration": (Config.ORCHESTRATION_AGENT_ID, OrchestrationAgent),
        "extractor": (Config.EXTRACTOR_AGENT_ID, ExtractorAgent),
        "evaluator": (Config.EVALUATOR_AGENT_ID, EvaluatorAgent),
        "scap": (Config.SCAP_AGENT_ID, SCAPAgent)
    }
    
    if agent_name not in agent_map:
        print(f"Unknown agent: {agent_name}")
        print(f"Available agents: {', '.join(agent_map.keys())}")
        sys.exit(1)
    
    agent_id, agent_class = agent_map[agent_name]
    
    if agent_name == "orchestration":
        # Orchestration agent runs API server in sync mode
        run_orchestration_agent()
    else:
        # Other agents run in async message loop
        await run_agent(agent_id, agent_class)


if __name__ == "__main__":
    if sys.argv[1] == "orchestration":
        run_orchestration_agent()
    else:
        asyncio.run(main())

