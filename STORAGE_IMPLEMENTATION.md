# Storage Backend Implementation

## Overview

The system now supports **configurable storage backends** - you can use either **PostgreSQL** or **Azure Cosmos DB**. The storage backend is automatically selected based on your configuration.

## Architecture

### Storage Abstraction Layer

A `StorageClient` abstract base class defines the interface that all storage backends must implement:

```python
class StorageClient(ABC):
    def save_state(...)
    def get_state(...)
    def save_task(...)
    def get_task(...)
    def save_conversation(...)
    def get_conversation_history(...)
    def save_transactions(...)
    def get_transactions(...)
```

### Implementation Classes

1. **CosmosDBClient** - Implements `StorageClient` for Azure Cosmos DB
2. **PostgreSQLClient** - Implements `StorageClient` for PostgreSQL

### Factory Pattern

The `create_storage_client()` function automatically selects the appropriate backend:

```python
def create_storage_client() -> StorageClient:
    if Config.POSTGRES_CONNECTION_STRING:
        return PostgreSQLClient()
    elif Config.COSMOS_ENDPOINT and Config.COSMOS_KEY:
        return CosmosDBClient()
    else:
        raise ValueError("No storage backend configured")
```

## PostgreSQL Implementation

### Features

- **Connection Pooling**: Uses `ThreadedConnectionPool` for efficient connection management
- **JSONB Storage**: Uses PostgreSQL's JSONB type for flexible JSON storage
- **Automatic Schema Creation**: Creates tables and indexes on initialization
- **ACID Transactions**: Full transaction support with rollback on errors

### Schema

```sql
-- Agent states
CREATE TABLE agent_states (
    id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    state_id VARCHAR(255) NOT NULL,
    state JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, state_id)
);

-- Agent tasks
CREATE TABLE agent_tasks (
    id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    task_data JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, task_id)
);

-- Conversations
CREATE TABLE conversations (
    id VARCHAR(255) PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    message JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions
CREATE TABLE transactions (
    id VARCHAR(255) PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    transaction JSONB NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

- `idx_agent_states_agent_state` on `(agent_id, state_id)`
- `idx_agent_tasks_agent_task` on `(agent_id, task_id)`
- `idx_conversations_conv_id` on `(conversation_id)`
- `idx_transactions_case_id` on `(case_id)`

## Cosmos DB Implementation

### Features

- **Container-based**: Uses Cosmos DB containers (similar to tables)
- **Automatic Creation**: Creates database and containers if they don't exist
- **Partition Key**: Uses `/id` as partition key for efficient queries
- **NoSQL**: Document-based storage with flexible schema

### Containers

- `agent_states` - Agent workflow states
- `agent_tasks` - Task execution details
- `conversations` - Conversation history
- `transactions` - Transaction data

## Code Changes

### Updated Files

1. **shared/storage_client.py** - New abstraction layer
2. **shared/postgres_client.py** - New PostgreSQL implementation
3. **shared/cosmos_client.py** - Updated to implement `StorageClient`
4. **config.py** - Added `POSTGRES_CONNECTION_STRING` configuration
5. **main.py** - Uses `create_storage_client()` factory
6. **agents/base_agent.py** - Updated type hints to use `StorageClient`
7. **shared/deep_agent.py** - Updated to use `StorageClient`
8. **shared/state_manager.py** - Updated to use `StorageClient`
9. **requirements.txt** - Added `psycopg2-binary`

### Backward Compatibility

- Parameter names remain `cosmos_client` for backward compatibility
- All existing code works without changes
- Storage backend is transparent to agents

## Usage

### Configuration

**PostgreSQL:**
```bash
POSTGRES_CONNECTION_STRING=postgresql://user:password@host:5432/database
```

**Cosmos DB:**
```bash
COSMOS_ENDPOINT=https://account.documents.azure.com:443/
COSMOS_KEY=your-key
COSMOS_DATABASE_NAME=transaction_review
```

### Code Usage

```python
from shared.storage_client import create_storage_client

# Automatically selects backend based on config
storage = create_storage_client()

# Use storage (same interface for both backends)
storage.save_state("agent-id", "state-id", {"data": "value"})
state = storage.get_state("agent-id", "state-id")
```

## Migration

To switch storage backends:

1. Update `.env` with new backend configuration
2. Restart agents
3. System will use new backend automatically

**Note**: Data is not automatically migrated. You'll need to export/import data manually if switching backends.

## Benefits

1. **Flexibility**: Choose the storage backend that fits your needs
2. **Cost Optimization**: Use PostgreSQL for lower costs, Cosmos DB for global scale
3. **Development**: Use local PostgreSQL for development
4. **Production**: Use managed PostgreSQL or Cosmos DB for production
5. **Transparency**: Same code works with both backends

## Testing

Both storage backends can be tested independently:

```python
# Test PostgreSQL
POSTGRES_CONNECTION_STRING=postgresql://... python test.py

# Test Cosmos DB
COSMOS_ENDPOINT=... COSMOS_KEY=... python test.py
```

## Performance

### PostgreSQL
- Better for complex queries
- Lower latency for local deployments
- Cost-effective for high-volume operations
- Connection pooling for efficiency

### Cosmos DB
- Better for global distribution
- Automatic scaling
- Higher throughput for read-heavy workloads
- Higher cost for high-volume operations

