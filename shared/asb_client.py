"""Azure Service Bus client for A2A message communication."""
import asyncio
import logging
from typing import Callable, Optional, Any
from azure.servicebus import ServiceBusClient, ServiceBusMessage, ServiceBusReceiver
from azure.servicebus.aio import ServiceBusClient as AsyncServiceBusClient
from azure.servicebus.aio.management import ServiceBusAdministrationClient
from config import Config
from shared.a2a_message import A2AMessageWrapper, message_to_json

logger = logging.getLogger(__name__)


class ASBClient:
    """Azure Service Bus client for sending and receiving A2A messages."""
    
    def __init__(self, connection_string: str = None, topic_name: str = None):
        self.connection_string = connection_string or Config.ASB_CONNECTION_STRING
        self.topic_name = topic_name or Config.ASB_TOPIC_NAME
        self.client: Optional[AsyncServiceBusClient] = None
        self.receiver: Optional[ServiceBusReceiver] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = AsyncServiceBusClient.from_connection_string(self.connection_string)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.receiver:
            await self.receiver.close()
        if self.client:
            await self.client.close()
    
    async def send_message(self, message: A2AMessageWrapper, agent_id: str):
        """Send A2A message to Azure Service Bus topic."""
        try:
            async with self.client:
                sender = self.client.get_topic_sender(topic_name=self.topic_name)
                
                # Create Service Bus message with A2A message as body
                sb_message = ServiceBusMessage(
                    body=message.to_json().encode('utf-8'),
                    subject=message.to_agent,  # Use 'to' field for routing
                    application_properties={
                        "from_agent": message.from_agent,
                        "to_agent": message.to_agent,
                        "agent_id": agent_id,
                        "conversation_id": message.conversation_id or "",
                        "correlation_id": message.correlation_id or ""
                    }
                )
                
                await sender.send_messages(sb_message)
                logger.info(f"Message sent from {message.from_agent} to {message.to_agent}")
                
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            raise
    
    async def receive_messages(
        self,
        agent_id: str,
        message_handler: Callable[[A2AMessage], Any],
        max_wait_time: int = 5
    ):
        """Receive and process messages intended for this agent."""
        try:
            async with self.client:
                # Create subscription for this agent if it doesn't exist
                subscription_name = f"{agent_id}-subscription"
                
                # Get receiver for subscription
                receiver = self.client.get_subscription_receiver(
                    topic_name=self.topic_name,
                    subscription_name=subscription_name,
                    max_wait_time=max_wait_time
                )
                
                self.receiver = receiver
                
                async with receiver:
                    async for message in receiver:
                        try:
                            # Parse A2A message from Service Bus message
                            message_body = message.body.decode('utf-8')
                            import json
                            data = json.loads(message_body)
                            
                            # Check if message is intended for this agent
                            to_agent = data.get("to_agent", "")
                            if to_agent == agent_id:
                                logger.info(f"Received message for {agent_id} from {data.get('from_agent', 'unknown')}")
                                # Handle message (can be async or sync)
                                if asyncio.iscoroutinefunction(message_handler):
                                    await message_handler(data)
                                else:
                                    message_handler(data)
                                await receiver.complete_message(message)
                            else:
                                # Release message if not intended for this agent
                                await receiver.abandon_message(message)
                                
                        except Exception as e:
                            logger.error(f"Error processing message: {str(e)}")
                            await receiver.dead_letter_message(message)
                            
        except Exception as e:
            logger.error(f"Error receiving messages: {str(e)}")
            raise
    
    async def ensure_subscription_exists(self, agent_id: str):
        """Ensure subscription exists for the agent."""
        try:
            async with ServiceBusAdministrationClient.from_connection_string(
                self.connection_string
            ) as admin_client:
                subscription_name = f"{agent_id}-subscription"
                
                try:
                    await admin_client.get_subscription(
                        topic_name=self.topic_name,
                        subscription_name=subscription_name
                    )
                    logger.info(f"Subscription {subscription_name} already exists")
                except Exception:
                    # Create subscription with filter for this agent
                    await admin_client.create_subscription(
                        topic_name=self.topic_name,
                        subscription_name=subscription_name
                    )
                    logger.info(f"Created subscription {subscription_name}")
                    
        except Exception as e:
            logger.warning(f"Could not ensure subscription exists: {str(e)}")

