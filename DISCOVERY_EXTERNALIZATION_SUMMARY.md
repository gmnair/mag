# Discovery Externalization Summary

## Overview

Agent discovery and MCP (Model Context Protocol) server discovery have been externalized to YAML configuration files. The system supports both static definitions and dynamic discovery from multiple sources.

## Changes Made

### 1. Created Discovery System

**New Files**:
- `discovery/discovery_config.yaml` - External discovery configuration
- `discovery/discovery_service.py` - Discovery service implementation
- `discovery/__init__.py` - Package exports
- `DISCOVERY_SYSTEM.md` - Complete documentation

### 2. Updated Code

**Modified Files**:
- `shared/deep_agent.py` - Uses discovery service for agent and tool discovery
- `config.py` - Added `DISCOVERY_CONFIG_FILE` configuration
- `requirements.txt` - Added `httpx` (if not already present)

## Architecture

### Design Pattern: Service Locator

The discovery system uses the **Service Locator pattern**:
- Centralized discovery service
- Caching for performance
- Multiple discovery sources
- Fallback mechanisms

### Components

1. **DiscoveryService** - Main service for discovery operations
2. **DiscoveryMetadata** - Extracts and manages metadata from YAML
3. **Static Discovery** - YAML-defined agents and MCP servers
4. **Dynamic Discovery** - Runtime discovery from storage, APIs, etc.

## Agent Discovery

### Before

```python
async def _discover_agents(self, state: DeepAgentState):
    from config import Config
    return [
        {"id": Config.ORCHESTRATION_AGENT_ID, "capabilities": "..."},
        # Hardcoded list
    ]
```

### After

```python
async def _discover_agents(self, state: DeepAgentState):
    from discovery import get_discovery_service
    service = get_discovery_service()
    return service.discover_agents()  # From YAML config
```

### Configuration

```yaml
agents:
  static:
    enabled: true
    agents:
      - id: orchestration-agent
        name: Orchestration Agent
        type: orchestration
        capabilities:
          - workflow_orchestration
          - api_endpoint
        endpoint: http://localhost:8000
        status: active
```

## MCP Server Discovery

### New Feature

MCP servers are now discoverable and integrated as tools:

```yaml
mcp_servers:
  static:
    enabled: true
    servers:
      - id: filesystem-mcp
        name: Filesystem MCP Server
        type: filesystem
        endpoint: stdio
        transport: stdio
        command: mcp-server-filesystem
        capabilities:
          - file_read
          - file_write
          - directory_listing
```

### Integration

MCP servers are automatically discovered and made available as tools in Deep Agent:

```python
tools = await deep_agent._discover_tools(state)
# Returns tools including MCP servers
```

## Discovery Sources

### Static Discovery

- **YAML Configuration**: Agents and MCP servers defined in config file
- **Fast**: No network calls
- **Reliable**: Always available
- **Good for**: Core, stable agents/servers

### Dynamic Discovery

Supports multiple sources:

1. **Storage** (Cosmos DB/PostgreSQL)
   - Query agent/MCP server registry
   - Supports runtime registration

2. **Service Bus**
   - Listen to discovery topics
   - Real-time agent announcements

3. **API Endpoints**
   - Query REST APIs
   - External registries

4. **MCP Protocol**
   - Standard MCP discovery
   - MCP server registries

## Features

### 1. Capability-Based Discovery

```python
# Find agents by capability
extractors = service.find_agents_by_capability("transaction_extraction")

# Find MCP servers by capability
file_servers = service.find_mcp_servers_by_capability("file_read")
```

### 2. Caching

- Results cached for performance
- Configurable TTL (default: 5 minutes)
- Manual refresh available

### 3. Environment Variable Resolution

```yaml
servers:
  - id: github-mcp
    args:
      - --token
      - ${GITHUB_TOKEN}  # Resolved from environment
```

### 4. Fallback Support

- Falls back to static if dynamic fails
- Configurable fallback behavior
- Error handling and logging

## Usage

### Basic Usage

```python
from discovery import get_discovery_service

service = get_discovery_service()

# Discover all agents
agents = service.discover_agents()

# Discover all MCP servers
mcp_servers = service.discover_mcp_servers()

# Get specific entity
agent = service.get_agent("orchestration-agent")
mcp_server = service.get_mcp_server("filesystem-mcp")

# Find by capability
agents = service.find_agents_by_capability("transaction_extraction")
```

### In Deep Agent

Automatically integrated:
- **Sense Phase**: Discovers agents and tools (including MCP servers)
- **Perceive Phase**: Uses discovered capabilities
- **Plan Phase**: Considers available agents and MCP servers

## Configuration

### Environment Variable

```bash
DISCOVERY_CONFIG_FILE=discovery/custom_discovery_config.yaml
```

### Default Location

If not specified, uses: `discovery/discovery_config.yaml`

## MCP Server Types Supported

1. **Filesystem MCP** - File operations
2. **Database MCP** - Database queries
3. **Web MCP** - Web search and scraping
4. **GitHub MCP** - GitHub operations
5. **Custom MCP** - Any MCP-compatible server

## Benefits

1. **Externalized Configuration**: All discovery config in YAML
2. **Multi-Source Discovery**: Static and dynamic sources
3. **MCP Integration**: Native MCP server support
4. **Capability-Based**: Find by capabilities
5. **Caching**: Performance optimization
6. **Extensibility**: Easy to add new discovery sources
7. **Fallback**: Graceful degradation

## Migration

### Before

- Hardcoded agent list in code
- No MCP server discovery
- Manual agent management

### After

- YAML-based configuration
- MCP server discovery
- Dynamic agent discovery
- Capability-based queries

## Future Enhancements

1. **Health Monitoring**: Track agent/server health
2. **Auto-Registration**: Agents register themselves
3. **Service Mesh Integration**: Discover from service mesh
4. **MCP Client**: Direct MCP protocol client
5. **Discovery Events**: Event-driven updates
6. **Load Balancing**: Distribute across multiple instances

