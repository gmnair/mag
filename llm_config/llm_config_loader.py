"""Tool to extract LLM configuration metadata from YAML."""
import logging
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


class LLMConfigMetadata:
    """Metadata extracted from LLM configuration."""
    
    def __init__(self, config_data: Dict[str, Any]):
        self.config_data = config_data
        self.active_provider = config_data.get("active_provider", "openai")
        self.providers = config_data.get("providers", {})
        self.defaults = config_data.get("defaults", {})
        self.model_overrides = config_data.get("model_overrides", {})
    
    def get_provider_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        provider = provider_name or self.active_provider
        
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not found in configuration")
        
        provider_config = self.providers[provider].copy()
        
        # Check if provider is enabled
        if not provider_config.get("enabled", False):
            raise ValueError(f"Provider '{provider}' is not enabled")
        
        # Resolve environment variables
        provider_config = self._resolve_env_vars(provider_config)
        
        # Apply defaults
        provider_config = self._apply_defaults(provider_config)
        
        # Apply model-specific overrides
        model = provider_config.get("model")
        if model and model in self.model_overrides:
            provider_config.update(self.model_overrides[model])
        
        return provider_config
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variable references in config."""
        resolved = {}
        for key, value in config.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract environment variable name
                env_var = value[2:-1]
                resolved[key] = os.getenv(env_var, "")
            else:
                resolved[key] = value
        return resolved
    
    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values to config."""
        for key, default_value in self.defaults.items():
            if key not in config:
                config[key] = default_value
        return config
    
    def get_active_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the active provider."""
        return self.get_provider_config(self.active_provider)
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled."""
        if provider_name not in self.providers:
            return False
        return self.providers[provider_name].get("enabled", False)
    
    def list_available_providers(self) -> list:
        """List all available providers."""
        return list(self.providers.keys())
    
    def list_enabled_providers(self) -> list:
        """List all enabled providers."""
        return [
            name for name, config in self.providers.items()
            if config.get("enabled", False)
        ]


class LLMConfigLoader:
    """Tool to load and extract LLM configuration metadata from YAML."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or getattr(Config, 'LLM_CONFIG_FILE', 'llm_config/llm_config.yaml')
        self.metadata: Optional[LLMConfigMetadata] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            config_path = Path(self.config_file)
            
            if not config_path.exists():
                logger.warning(f"LLM config file not found: {self.config_file}, using defaults")
                self.metadata = self._create_default_metadata()
                return
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            
            self.metadata = LLMConfigMetadata(config_data)
            logger.info(f"Loaded LLM configuration from {self.config_file}")
            logger.info(f"Active provider: {self.metadata.active_provider}")
            
        except Exception as e:
            logger.error(f"Error loading LLM config: {str(e)}")
            self.metadata = self._create_default_metadata()
    
    def _create_default_metadata(self) -> LLMConfigMetadata:
        """Create default metadata if config file is not found."""
        default_config = {
            "active_provider": "openai",
            "providers": {
                "openai": {
                    "enabled": True,
                    "api_key": os.getenv("OPENAI_API_KEY", ""),
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "max_tokens": 2000,
                    "timeout": 60,
                    "max_retries": 3
                }
            },
            "defaults": {
                "temperature": 0.3,
                "max_tokens": 2000,
                "timeout": 60,
                "max_retries": 3
            },
            "model_overrides": {}
        }
        return LLMConfigMetadata(default_config)
    
    def get_metadata(self) -> LLMConfigMetadata:
        """Get the loaded metadata."""
        if self.metadata is None:
            self._load_config()
        return self.metadata
    
    def extract_config(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """Extract configuration for a specific provider."""
        metadata = self.get_metadata()
        return metadata.get_provider_config(provider_name)
    
    def get_active_provider_config(self) -> Dict[str, Any]:
        """Get configuration for the active provider."""
        metadata = self.get_metadata()
        return metadata.get_active_provider_config()


# Global config loader instance
_config_loader: Optional[LLMConfigLoader] = None


def get_llm_config_loader() -> LLMConfigLoader:
    """Get global LLM config loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = LLMConfigLoader()
    return _config_loader

