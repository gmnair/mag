"""Factory to create LLM instances based on configuration."""
import logging
from typing import Optional, Any
from abc import ABC, abstractmethod

from llm_config.llm_config_loader import get_llm_config_loader, LLMConfigLoader

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory to create LLM instances from configuration."""
    
    def __init__(self, config_loader: Optional[LLMConfigLoader] = None):
        self.config_loader = config_loader or get_llm_config_loader()
    
    def create_llm(self, provider_name: Optional[str] = None, **override_params) -> Any:
        """Create an LLM instance based on configuration.
        
        Args:
            provider_name: Optional provider name. If None, uses active provider from config.
            **override_params: Parameters to override from config.
        
        Returns:
            LLM instance (ChatOpenAI, ChatAnthropic, etc.)
        """
        try:
            # Get provider configuration
            if provider_name:
                config = self.config_loader.extract_config(provider_name)
                provider = provider_name
            else:
                metadata = self.config_loader.get_metadata()
                provider = metadata.active_provider
                config = metadata.get_active_provider_config()
            
            # Set provider name in config for reference
            config["provider"] = provider
            
            # Apply overrides
            config.update(override_params)
            
            # Check if API key is present
            api_key = config.get("api_key")
            if not api_key:
                logger.warning(f"No API key found for provider '{provider}', LLM will be None")
                return None
            
            # Create appropriate LLM instance based on provider
            if provider == "openai":
                return self._create_openai_llm(config)
            elif provider == "anthropic":
                return self._create_anthropic_llm(config)
            elif provider == "google":
                return self._create_google_llm(config)
            elif provider == "deepseek":
                return self._create_deepseek_llm(config)
            elif provider == "azure_openai":
                return self._create_azure_openai_llm(config)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            logger.error(f"Error creating LLM: {str(e)}")
            return None
    
    def _create_openai_llm(self, config: dict):
        """Create OpenAI LLM instance."""
        try:
            from langchain_openai import ChatOpenAI
            
            llm_params = {
                "model": config.get("model", "gpt-4"),
                "temperature": config.get("temperature", 0.3),
                "api_key": config.get("api_key"),
                "max_tokens": config.get("max_tokens"),
                "timeout": config.get("timeout", 60),
                "max_retries": config.get("max_retries", 3),
            }
            
            # Optional parameters
            if config.get("base_url"):
                llm_params["base_url"] = config["base_url"]
            if config.get("organization"):
                llm_params["organization"] = config["organization"]
            
            # Remove None values
            llm_params = {k: v for k, v in llm_params.items() if v is not None}
            
            return ChatOpenAI(**llm_params)
            
        except ImportError:
            logger.error("langchain-openai not installed. Install with: pip install langchain-openai")
            return None
    
    def _create_anthropic_llm(self, config: dict):
        """Create Anthropic (Claude) LLM instance."""
        try:
            from langchain_anthropic import ChatAnthropic
            
            llm_params = {
                "model": config.get("model", "claude-3-opus-20240229"),
                "temperature": config.get("temperature", 0.3),
                "api_key": config.get("api_key"),
                "max_tokens": config.get("max_tokens"),
                "timeout": config.get("timeout", 60),
                "max_retries": config.get("max_retries", 3),
            }
            
            # Remove None values
            llm_params = {k: v for k, v in llm_params.items() if v is not None}
            
            return ChatAnthropic(**llm_params)
            
        except ImportError:
            logger.error("langchain-anthropic not installed. Install with: pip install langchain-anthropic")
            return None
    
    def _create_google_llm(self, config: dict):
        """Create Google (Gemini) LLM instance."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            llm_params = {
                "model": config.get("model", "gemini-pro"),
                "temperature": config.get("temperature", 0.3),
                "google_api_key": config.get("api_key"),
                "max_output_tokens": config.get("max_tokens"),
                "timeout": config.get("timeout", 60),
            }
            
            # Remove None values
            llm_params = {k: v for k, v in llm_params.items() if v is not None}
            
            return ChatGoogleGenerativeAI(**llm_params)
            
        except ImportError:
            logger.error("langchain-google-genai not installed. Install with: pip install langchain-google-genai")
            return None
    
    def _create_deepseek_llm(self, config: dict):
        """Create DeepSeek LLM instance."""
        try:
            from langchain_openai import ChatOpenAI
            
            # DeepSeek uses OpenAI-compatible API
            llm_params = {
                "model": config.get("model", "deepseek-chat"),
                "temperature": config.get("temperature", 0.3),
                "api_key": config.get("api_key"),
                "max_tokens": config.get("max_tokens"),
                "timeout": config.get("timeout", 60),
                "max_retries": config.get("max_retries", 3),
            }
            
            # DeepSeek requires custom base_url
            base_url = config.get("base_url", "https://api.deepseek.com")
            if base_url:
                llm_params["base_url"] = base_url
            
            # Remove None values
            llm_params = {k: v for k, v in llm_params.items() if v is not None}
            
            return ChatOpenAI(**llm_params)
            
        except ImportError:
            logger.error("langchain-openai not installed. Install with: pip install langchain-openai")
            return None
    
    def _create_azure_openai_llm(self, config: dict):
        """Create Azure OpenAI LLM instance."""
        try:
            from langchain_openai import AzureChatOpenAI
            
            llm_params = {
                "azure_deployment": config.get("deployment_name", config.get("model")),
                "model": config.get("model", "gpt-4"),
                "temperature": config.get("temperature", 0.3),
                "api_key": config.get("api_key"),
                "azure_endpoint": config.get("azure_endpoint"),
                "api_version": config.get("api_version", "2024-02-15-preview"),
                "max_tokens": config.get("max_tokens"),
                "timeout": config.get("timeout", 60),
                "max_retries": config.get("max_retries", 3),
            }
            
            # Remove None values
            llm_params = {k: v for k, v in llm_params.items() if v is not None}
            
            return AzureChatOpenAI(**llm_params)
            
        except ImportError:
            logger.error("langchain-openai not installed. Install with: pip install langchain-openai")
            return None


# Global factory instance
_llm_factory: Optional[LLMFactory] = None


def get_llm_factory() -> LLMFactory:
    """Get global LLM factory instance."""
    global _llm_factory
    if _llm_factory is None:
        _llm_factory = LLMFactory()
    return _llm_factory


def create_llm(provider_name: Optional[str] = None, **override_params) -> Any:
    """Convenience function to create an LLM instance."""
    factory = get_llm_factory()
    return factory.create_llm(provider_name, **override_params)

