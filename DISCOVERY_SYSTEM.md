# Discovery System Documentation

## Overview

The discovery system externalizes agent and MCP (Model Context Protocol) server discovery to YAML configuration files. It supports both static definitions and dynamic discovery from multiple sources.

## Architecture

### Components

1. **DiscoveryService** - Main service for discovering agents and MCP servers
2. **DiscoveryMetadata** - Extracts and manages discovery metadata from YAML
3. **discovery_config.yaml** - External configuration file

### Design Pattern: Service Locator

The system uses a **Service Locator pattern**:
- Centralized discovery service
- Caching for performance
- Multiple discovery sources (static, dynamic)
- Fallback mechanisms

## Agent Discovery

### Static Agent Definitions

Agents are defined in `discovery/discovery_config.yaml`:

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

### Agent Properties

- **id**: Unique agent identifier
- **name**: Human-readable name
- **type**: Agent type (orchestration, extractor, evaluator, scap)
- **capabilities**: List of agent capabilities
- **endpoint**: API endpoint (if applicable)
- **status**: Agent status (active, inactive, maintenance)
- **metadata**: Additional metadata (description, version, etc.)

### Dynamic Agent Discovery

Supports discovery from multiple sources:

1. **Storage** (Cosmos DB/PostgreSQL)
   ```yaml
   - type: storage
     enabled: true
     container: agent_registry
     query: "SELECT * FROM agent_registry WHERE status = 'active'"
   ```

2. **Service Bus**
   ```yaml
   - type: service_bus
     enabled: false
     topic: agent-discovery
     subscription: agent-registry
   ```

3. **API Endpoint**
   ```yaml
   - type: api
     enabled: false
     endpoint: http://agent-registry:8080/api/v1/agents
     refresh_interval: 300
   ```

## MCP Server Discovery

### Static MCP Server Definitions

MCP servers are defined in the same configuration file:

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

### MCP Server Properties

- **id**: Unique server identifier
- **name**: Human-readable name
- **type**: Server type (filesystem, database, web, github, etc.)
- **endpoint**: Server endpoint (stdio, http URL, etc.)
- **transport**: Transport protocol (stdio, http, websocket)
- **command**: Command to start server (for stdio)
- **args**: Command arguments
- **capabilities**: List of server capabilities
- **metadata**: Additional metadata

### Dynamic MCP Server Discovery

Supports discovery from:

1. **Storage**
   ```yaml
   - type: storage
     enabled: true
     container: mcp_server_registry
     query: "SELECT * FROM mcp_server_registry WHERE status = 'active'"
   ```

2. **MCP Protocol**
   ```yaml
   - type: mcp_protocol
     enabled: false
     discovery_endpoint: http://mcp-registry:8080/discover
     refresh_interval: 300
   ```

## Usage

### Basic Usage

```python
from discovery import get_discovery_service

service = get_discovery_service()

# Discover all agents
agents = service.discover_agents()

# Discover all MCP servers
mcp_servers = service.discover_mcp_servers()

# Get specific agent
agent = service.get_agent("orchestration-agent")

# Get specific MCP server
mcp_server = service.get_mcp_server("filesystem-mcp")

# Find by capability
agents = service.find_agents_by_capability("transaction_extraction")
mcp_servers = service.find_mcp_servers_by_capability("file_read")
```

### In Deep Agent

The discovery system is automatically integrated into Deep Agent:

- **Agent Discovery**: `_discover_agents()` uses discovery service
- **Tool Discovery**: `_discover_tools()` includes MCP servers as tools

## Configuration

### Environment Variables

```bash
DISCOVERY_CONFIG_FILE=discovery/custom_discovery_config.yaml
```

### Default Location

If not specified, uses: `discovery/discovery_config.yaml`

## Discovery Sources

### 1. Static Configuration

- Defined in YAML file
- Fast and reliable
- No network calls
- Good for known, stable agents/servers

### 2. Storage-Based Discovery

- Query from Cosmos DB or PostgreSQL
- Supports dynamic agent registration
- Requires agent registry container/table

### 3. Service Bus Discovery

- Listen to Service Bus topic
- Real-time agent announcements
- Supports agent lifecycle events

### 4. API-Based Discovery

- Query REST API endpoint
- Supports external agent registries
- Configurable refresh interval

### 5. MCP Protocol Discovery

- Use MCP protocol for server discovery
- Standard MCP discovery endpoint
- Supports MCP server registries

## Caching

Discovery results are cached for performance:

- **Cache TTL**: Configurable (default: 5 minutes)
- **Manual Refresh**: `service.refresh_cache()`
- **On-Demand Refresh**: Disable cache for fresh results

```yaml
settings:
  cache_ttl: 300  # 5 minutes
  refresh_on_demand: true
  fallback_to_static: true
```

## Capability-Based Discovery

Find agents or MCP servers by capability:

```python
# Find agents that can extract transactions
extractors = service.find_agents_by_capability("transaction_extraction")

# Find MCP servers that can read files
file_servers = service.find_mcp_servers_by_capability("file_read")
```

## MCP Server Integration

MCP servers are automatically discovered and made available as tools:

```python
# MCP servers appear in tool discovery
tools = await deep_agent._discover_tools(state)
# Returns: [
#   {"name": "cosmos_db", "type": "storage", ...},
#   {"name": "filesystem-mcp", "type": "mcp_server", "mcp_type": "filesystem", ...},
#   ...
# ]
```

## Example Configurations

### Minimal Configuration

```yaml
agents:
  static:
    enabled: true
    agents:
      - id: orchestration-agent
        capabilities: ["workflow_orchestration"]

mcp_servers:
  static:
    enabled: false
```

### Full Configuration

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
        metadata:
          description: "Root agent"
          version: "1.0.0"
  
  dynamic:
    enabled: true
    sources:
      - type: storage
        enabled: true
        container: agent_registry

mcp_servers:
  static:
    enabled: true
    servers:
      - id: filesystem-mcp
        name: Filesystem MCP
        type: filesystem
        endpoint: stdio
        transport: stdio
        command: mcp-server-filesystem
        capabilities:
          - file_read
          - file_write
```

## Environment Variable Resolution

Configuration supports environment variables:

```yaml
servers:
  - id: github-mcp
    args:
      - --token
      - ${GITHUB_TOKEN}  # Resolved from environment
```

## Best Practices

1. **Static for Core Agents**: Define core agents statically
2. **Dynamic for Extensions**: Use dynamic discovery for plugins/extensions
3. **Capability Tags**: Use consistent capability names
4. **Health Checks**: Monitor agent/server health
5. **Caching**: Use caching for performance
6. **Fallback**: Enable fallback to static if dynamic fails

## Troubleshooting

### Agents Not Discovered

- Check agent is enabled in config
- Verify agent ID matches
- Check dynamic sources are enabled
- Review logs for discovery errors

### MCP Servers Not Available

- Verify MCP server is enabled
- Check transport and endpoint settings
- Ensure MCP server process is running
- Review capability names

### Cache Issues

- Call `refresh_cache()` to clear cache
- Disable cache for testing: `discover_agents(use_cache=False)`
- Adjust `cache_ttl` in settings

## Integration with Deep Agent

The discovery system is automatically used in:

1. **Sense Phase**: Discovers agents and tools (including MCP servers)
2. **Perceive Phase**: Uses discovered capabilities in planning
3. **Plan Phase**: Considers available agents and MCP servers

## Future Enhancements

1. **Health Monitoring**: Track agent/server health
2. **Auto-Registration**: Agents register themselves
3. **Service Mesh Integration**: Discover from service mesh
4. **MCP Client Integration**: Direct MCP protocol support
5. **Discovery Events**: Event-driven discovery updates

