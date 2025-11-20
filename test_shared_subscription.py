"""Test client for testing the shared subscription functionality."""
import asyncio
import json
import logging
from shared.asb_client import ASBClient
from shared.a2a_message import create_a2a_message, A2AMessageWrapper
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_shared_subscription():
    """Test that multiple agents can use the same subscription and filter by to_agent."""
    
    # Create ASB client
    asb_client = ASBClient()
    
    # Ensure shared subscription exists
    await asb_client.ensure_subscription_exists()
    
    # Test messages for different agents
    test_messages = [
        {
            "from_agent": "test-sender",
            "to_agent": Config.EXTRACTOR_AGENT_ID,
            "payload": {"case_id": "TEST-001", "action": "test_extract"}
        },
        {
            "from_agent": "test-sender", 
            "to_agent": Config.EVALUATOR_AGENT_ID,
            "payload": {"case_id": "TEST-002", "action": "test_evaluate"}
        },
        {
            "from_agent": "test-sender",
            "to_agent": Config.SCAP_AGENT_ID,
            "payload": {"case_id": "TEST-003", "action": "test_scap"}
        }
    ]
    
    # Send test messages
    for msg_data in test_messages:
        message = create_a2a_message(
            message_id=f"test_{msg_data['to_agent']}",
            role="agent",
            text=f"Test message for {msg_data['to_agent']}",
            context_id="test_conversation"
        )
        
        wrapper = A2AMessageWrapper(
            message=message,
            from_agent=msg_data["from_agent"],
            to_agent=msg_data["to_agent"],
            payload=msg_data["payload"]
        )
        
        await asb_client.send_message(wrapper, msg_data["from_agent"])
        logger.info(f"Sent test message to {msg_data['to_agent']}")
    
    # Simulate agent message handlers
    received_messages = {}
    
    async def extractor_handler(message_data):
        received_messages[Config.EXTRACTOR_AGENT_ID] = message_data
        logger.info(f"Extractor agent received: {message_data.get('to_agent')}")
    
    async def evaluator_handler(message_data):
        received_messages[Config.EVALUATOR_AGENT_ID] = message_data
        logger.info(f"Evaluator agent received: {message_data.get('to_agent')}")
    
    async def scap_handler(message_data):
        received_messages[Config.SCAP_AGENT_ID] = message_data
        logger.info(f"SCAP agent received: {message_data.get('to_agent')}")
    
    # Test receiving with different agent IDs
    logger.info("Testing message filtering by to_agent...")
    
    # Simulate extractor agent receiving
    await asb_client.receive_messages(Config.EXTRACTOR_AGENT_ID, extractor_handler, max_wait_time=2)
    
    # Simulate evaluator agent receiving  
    await asb_client.receive_messages(Config.EVALUATOR_AGENT_ID, evaluator_handler, max_wait_time=2)
    
    # Simulate SCAP agent receiving
    await asb_client.receive_messages(Config.SCAP_AGENT_ID, scap_handler, max_wait_time=2)
    
    # Verify each agent only received their intended messages
    for agent_id in [Config.EXTRACTOR_AGENT_ID, Config.EVALUATOR_AGENT_ID, Config.SCAP_AGENT_ID]:
        if agent_id in received_messages:
            msg = received_messages[agent_id]
            if msg.get("to_agent") == agent_id:
                logger.info(f"✓ {agent_id} correctly received its message")
            else:
                logger.error(f"✗ {agent_id} received wrong message intended for {msg.get('to_agent')}")
        else:
            logger.warning(f"⚠ {agent_id} did not receive any message")
    
    logger.info("Shared subscription test completed")


if __name__ == "__main__":
    asyncio.run(test_shared_subscription())