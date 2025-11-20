"""Discovery service for agents and MCP servers."""
import logging
import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


class DiscoveryMetadata:
    """Metadata extracted from discovery configuration."""
    
    def __init__(self, config_data: Dict[str, Any]):
        self.config_data = config_data
        self.agents_config = config_data.get("agents", {})
        self.mcp_servers_config = config_data.get("mcp_servers", {})
        self.settings = config_data.get("settings", {})
    
    def get_agents(self, include_dynamic: bool = True) -> List[Dict[str, Any]]:
        """Get all available agents."""
        agents = []
        
        # Get static agents
        if self.agents_config.get("static", {}).get("enabled", True):
            static_agents = self.agents_config.get("static", {}).get("agents", [])
            agents.extend(self._resolve_env_vars_list(static_agents))
        
        # Get dynamic agents if enabled
        if include_dynamic and self.agents_config.get("dynamic", {}).get("enabled", True):
            dynamic_agents = self._discover_dynamic_agents()
            agents.extend(dynamic_agents)
        
        return agents
    
    def get_mcp_servers(self, include_dynamic: bool = True) -> List[Dict[str, Any]]:
        """Get all available MCP servers."""
        servers = []
        
        # Get static MCP servers
        if self.mcp_servers_config.get("static", {}).get("enabled", True):
            static_servers = self.mcp_servers_config.get("static", {}).get("servers", [])
            servers.extend(self._resolve_env_vars_list(static_servers))
        
        # Get dynamic MCP servers if enabled
        if include_dynamic and self.mcp_servers_config.get("dynamic", {}).get("enabled", True):
            dynamic_servers = self._discover_dynamic_mcp_servers()
            servers.extend(dynamic_servers)
        
        return servers
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific agent by ID."""
        agents = self.get_agents()
        for agent in agents:
            if agent.get("id") == agent_id:
                return agent
        return None
    
    def get_mcp_server_by_id(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server by ID."""
        servers = self.get_mcp_servers()
        for server in servers:
            if server.get("id") == server_id:
                return server
        return None
    
    def get_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Get agents that have a specific capability."""
        agents = self.get_agents()
        return [
            agent for agent in agents
            if capability in agent.get("capabilities", [])
        ]
    
    def get_mcp_servers_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Get MCP servers that have a specific capability."""
        servers = self.get_mcp_servers()
        return [
            server for server in servers
            if capability in server.get("capabilities", [])
        ]
    
    def _resolve_env_vars_list(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve environment variables in a list of items."""
        resolved = []
        for item in items:
            resolved_item = self._resolve_env_vars(item)
            resolved.append(resolved_item)
        return resolved
    
    def _resolve_env_vars(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variable references in an item."""
        resolved = {}
        for key, value in item.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved[key] = os.getenv(env_var, "")
            elif isinstance(value, list):
                resolved[key] = [
                    os.getenv(v[2:-1], "") if isinstance(v, str) and v.startswith("${") and v.endswith("}")
                    else self._resolve_env_vars(v) if isinstance(v, dict)
                    else v
                    for v in value
                ]
            elif isinstance(value, dict):
                resolved[key] = self._resolve_env_vars(value)
            else:
                resolved[key] = value
        return resolved
    
    def _discover_dynamic_agents(self) -> List[Dict[str, Any]]:
        """Discover agents from dynamic sources."""
        agents = []
        dynamic_config = self.agents_config.get("dynamic", {})
        sources = dynamic_config.get("sources", [])
        
        for source in sources:
            if not source.get("enabled", False):
                continue
            
            source_type = source.get("type")
            try:
                if source_type == "storage":
                    agents.extend(self._discover_from_storage(source, "agent"))
                elif source_type == "service_bus":
                    agents.extend(self._discover_from_service_bus(source))
                elif source_type == "api":
                    agents.extend(self._discover_from_api(source))
            except Exception as e:
                logger.warning(f"Error discovering agents from {source_type}: {str(e)}")
                if self.settings.get("fallback_to_static", True):
                    continue  # Fall back to static
        
        return agents
    
    def _discover_dynamic_mcp_servers(self) -> List[Dict[str, Any]]:
        """Discover MCP servers from dynamic sources."""
        servers = []
        dynamic_config = self.mcp_servers_config.get("dynamic", {})
        sources = dynamic_config.get("sources", [])
        
        for source in sources:
            if not source.get("enabled", False):
                continue
            
            source_type = source.get("type")
            try:
                if source_type == "storage":
                    servers.extend(self._discover_from_storage(source, "mcp"))
                elif source_type == "mcp_protocol":
                    servers.extend(self._discover_from_mcp_protocol(source))
            except Exception as e:
                logger.warning(f"Error discovering MCP servers from {source_type}: {str(e)}")
                if self.settings.get("fallback_to_static", True):
                    continue  # Fall back to static
        
        return servers
    
    def _discover_from_storage(self, source_config: Dict[str, Any], entity_type: str) -> List[Dict[str, Any]]:
        """Discover entities from storage (Cosmos DB/PostgreSQL)."""
        try:
            from shared.storage_client import create_storage_client
            
            storage = create_storage_client()
            container = source_config.get("container", f"{entity_type}_registry")
            query = source_config.get("query", f"SELECT * FROM {container}")
            
            # For now, return empty list - would need storage-specific query implementation
            # In production, this would query the storage backend
            logger.debug(f"Storage discovery for {entity_type} not fully implemented")
            return []
            
        except Exception as e:
            logger.error(f"Error discovering from storage: {str(e)}")
            return []
    
    def _discover_from_service_bus(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover agents from Service Bus."""
        # Would listen to Service Bus topic for agent announcements
        logger.debug("Service Bus discovery not fully implemented")
        return []
    
    def _discover_from_api(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover agents from API endpoint."""
        try:
            import httpx
            
            endpoint = source_config.get("endpoint")
            if not endpoint:
                return []
            
            with httpx.Client(timeout=10) as client:
                response = client.get(endpoint)
                if response.status_code == 200:
                    return response.json().get("agents", [])
            return []
            
        except ImportError:
            logger.warning("httpx not available for API discovery")
            return []
        except Exception as e:
            logger.error(f"Error discovering from API: {str(e)}")
            return []
    
    def _discover_from_mcp_protocol(self, source_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover MCP servers using MCP protocol."""
        try:
            import httpx
            
            endpoint = source_config.get("discovery_endpoint")
            if not endpoint:
                return []
            
            with httpx.Client(timeout=10) as client:
                response = client.get(endpoint)
                if response.status_code == 200:
                    return response.json().get("servers", [])
            return []
            
        except ImportError:
            logger.warning("httpx not available for MCP protocol discovery")
            return []
        except Exception as e:
            logger.error(f"Error discovering MCP servers: {str(e)}")
            return []


class DiscoveryService:
    """Service for discovering agents and MCP servers."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or getattr(Config, 'DISCOVERY_CONFIG_FILE', 'discovery/discovery_config.yaml')
        self.metadata: Optional[DiscoveryMetadata] = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 300  # 5 minutes default
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            config_path = Path(self.config_file)
            
            if not config_path.exists():
                logger.warning(f"Discovery config file not found: {self.config_file}, using defaults")
                self.metadata = self._create_default_metadata()
                return
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
            
            self.metadata = DiscoveryMetadata(config_data)
            self._cache_ttl = self.metadata.settings.get("cache_ttl", 300)
            logger.info(f"Loaded discovery configuration from {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error loading discovery config: {str(e)}")
            self.metadata = self._create_default_metadata()
    
    def _create_default_metadata(self) -> DiscoveryMetadata:
        """Create default metadata if config file is not found."""
        from config import Config
        
        default_config = {
            "agents": {
                "static": {
                    "enabled": True,
                    "agents": [
                        {
                            "id": Config.ORCHESTRATION_AGENT_ID,
                            "name": "Orchestration Agent",
                            "type": "orchestration",
                            "capabilities": ["workflow_orchestration"],
                            "status": "active"
                        },
                        {
                            "id": Config.EXTRACTOR_AGENT_ID,
                            "name": "Extractor Agent",
                            "type": "extractor",
                            "capabilities": ["transaction_extraction"],
                            "status": "active"
                        },
                        {
                            "id": Config.EVALUATOR_AGENT_ID,
                            "name": "Evaluator Agent",
                            "type": "evaluator",
                            "capabilities": ["transaction_evaluation"],
                            "status": "active"
                        },
                        {
                            "id": Config.SCAP_AGENT_ID,
                            "name": "SCAP Agent",
                            "type": "scap",
                            "capabilities": ["sensitive_country_validation"],
                            "status": "active"
                        }
                    ]
                },
                "dynamic": {"enabled": False, "sources": []}
            },
            "mcp_servers": {
                "static": {"enabled": True, "servers": []},
                "dynamic": {"enabled": False, "sources": []}
            },
            "settings": {
                "cache_ttl": 300,
                "fallback_to_static": True
            }
        }
        return DiscoveryMetadata(default_config)
    
    def get_metadata(self) -> DiscoveryMetadata:
        """Get the loaded metadata."""
        if self.metadata is None:
            self._load_config()
        return self.metadata
    
    def discover_agents(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Discover all available agents."""
        cache_key = "agents"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        metadata = self.get_metadata()
        agents = metadata.get_agents()
        
        if use_cache:
            self._cache[cache_key] = agents
        
        return agents
    
    def discover_mcp_servers(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Discover all available MCP servers."""
        cache_key = "mcp_servers"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        metadata = self.get_metadata()
        servers = metadata.get_mcp_servers()
        
        if use_cache:
            self._cache[cache_key] = servers
        
        return servers
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific agent by ID."""
        metadata = self.get_metadata()
        return metadata.get_agent_by_id(agent_id)
    
    def get_mcp_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server by ID."""
        metadata = self.get_metadata()
        return metadata.get_mcp_server_by_id(server_id)
    
    def find_agents_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find agents with a specific capability."""
        metadata = self.get_metadata()
        return metadata.get_agents_by_capability(capability)
    
    def find_mcp_servers_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Find MCP servers with a specific capability."""
        metadata = self.get_metadata()
        return metadata.get_mcp_servers_by_capability(capability)
    
    def refresh_cache(self):
        """Refresh the discovery cache."""
        self._cache.clear()
        logger.info("Discovery cache refreshed")


# Global discovery service instance
_discovery_service: Optional[DiscoveryService] = None


def get_discovery_service() -> DiscoveryService:
    """Get global discovery service instance."""
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = DiscoveryService()
    return _discovery_service

