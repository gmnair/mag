"""Configuration settings for the multi-agent transaction review system."""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # Azure Service Bus Configuration
    ASB_CONNECTION_STRING: str = os.getenv("ASB_CONNECTION_STRING", "")
    ASB_TOPIC_NAME: str = os.getenv("ASB_TOPIC_NAME", "a2a-messages")
    
    # Storage Configuration (PostgreSQL or Cosmos DB)
    POSTGRES_CONNECTION_STRING: str = os.getenv("POSTGRES_CONNECTION_STRING", "")
    
    # Azure Cosmos DB Configuration
    COSMOS_ENDPOINT: str = os.getenv("COSMOS_ENDPOINT", "")
    COSMOS_KEY: str = os.getenv("COSMOS_KEY", "")
    COSMOS_DATABASE_NAME: str = os.getenv("COSMOS_DATABASE_NAME", "transaction_review")
    COSMOS_STATE_CONTAINER: str = os.getenv("COSMOS_STATE_CONTAINER", "agent_states")
    COSMOS_TASK_CONTAINER: str = os.getenv("COSMOS_TASK_CONTAINER", "agent_tasks")
    COSMOS_CONVERSATION_CONTAINER: str = os.getenv("COSMOS_CONVERSATION_CONTAINER", "conversations")
    COSMOS_TRANSACTION_CONTAINER: str = os.getenv("COSMOS_TRANSACTION_CONTAINER", "transactions")
    
    # Agent Configuration
    ORCHESTRATION_AGENT_ID: str = "orchestration-agent"
    EXTRACTOR_AGENT_ID: str = "extractor-agent"
    EVALUATOR_AGENT_ID: str = "evaluator-agent"
    SCAP_AGENT_ID: str = "scap-agent"
    
    # LLM Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Rule Engine Configuration
    SCAP_RULE_THRESHOLD: float = float(os.getenv("SCAP_RULE_THRESHOLD", "1000.0"))
    SCAP_RULES_FILE: str = os.getenv("SCAP_RULES_FILE", "scap_rules.yaml")
    
    # A2A Protocol Configuration
    A2A_API_PORT: int = int(os.getenv("A2A_API_PORT", "8000"))
    A2A_API_HOST: str = os.getenv("A2A_API_HOST", "0.0.0.0")
    
    # Prompt Templates Configuration
    PROMPTS_CONFIG_FILE: str = os.getenv("PROMPTS_CONFIG_FILE", "prompts/prompts.yaml")
    
    # LLM Configuration File
    LLM_CONFIG_FILE: str = os.getenv("LLM_CONFIG_FILE", "llm_config/llm_config.yaml")
    
    # Discovery Configuration File
    DISCOVERY_CONFIG_FILE: str = os.getenv("DISCOVERY_CONFIG_FILE", "discovery/discovery_config.yaml")

