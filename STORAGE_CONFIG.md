# Storage Configuration Guide

The system supports two storage backends: **PostgreSQL** or **Azure Cosmos DB**. You can configure either one, and the system will automatically use the one that's configured.

## Configuration Priority

The system checks configuration in this order:
1. **PostgreSQL** - If `POSTGRES_CONNECTION_STRING` is provided, PostgreSQL will be used
2. **Cosmos DB** - If `COSMOS_ENDPOINT` and `COSMOS_KEY` are provided, Cosmos DB will be used
3. **Error** - If neither is configured, the system will raise an error

## PostgreSQL Configuration

### Connection String Format

```bash
POSTGRES_CONNECTION_STRING=postgresql://user:password@host:port/database
```

### Example

```bash
# Local PostgreSQL
POSTGRES_CONNECTION_STRING=postgresql://postgres:password@localhost:5432/transaction_review

# Azure Database for PostgreSQL
POSTGRES_CONNECTION_STRING=postgresql://user@server:password@server.postgres.database.azure.com:5432/database

# With SSL
POSTGRES_CONNECTION_STRING=postgresql://user:password@host:5432/database?sslmode=require
```

### Database Setup

The system will automatically create the following tables:
- `agent_states` - Stores agent workflow states
- `agent_tasks` - Stores task execution details
- `conversations` - Stores conversation history
- `transactions` - Stores transaction data

### Required PostgreSQL Extensions

The system uses JSONB for storing JSON data. PostgreSQL 9.4+ includes JSONB support by default.

## Azure Cosmos DB Configuration

### Required Environment Variables

```bash
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DATABASE_NAME=transaction_review
COSMOS_STATE_CONTAINER=agent_states
COSMOS_TASK_CONTAINER=agent_tasks
COSMOS_CONVERSATION_CONTAINER=conversations
COSMOS_TRANSACTION_CONTAINER=transactions
```

### Containers

The system will automatically create the following containers:
- `agent_states` - Stores agent workflow states
- `agent_tasks` - Stores task execution details
- `conversations` - Stores conversation history
- `transactions` - Stores transaction data

## Example .env File

### Using PostgreSQL

```bash
# Storage - PostgreSQL
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/transaction_review

# Azure Service Bus
ASB_CONNECTION_STRING=Endpoint=sb://...
ASB_TOPIC_NAME=a2a-messages

# OpenAI (optional)
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4
```

### Using Cosmos DB

```bash
# Storage - Cosmos DB
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DATABASE_NAME=transaction_review

# Azure Service Bus
ASB_CONNECTION_STRING=Endpoint=sb://...
ASB_TOPIC_NAME=a2a-messages

# OpenAI (optional)
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4
```

## Storage Features

Both storage backends support:

- **State Management**: Save and retrieve agent workflow states
- **Task Tracking**: Store task execution details and results
- **Conversation History**: Maintain conversation history across agents
- **Transaction Storage**: Store extracted transaction data

## Performance Considerations

### PostgreSQL
- Better for relational queries
- ACID transactions
- Lower cost for high-volume operations
- Requires connection pooling (handled automatically)

### Cosmos DB
- Better for global distribution
- Automatic scaling
- NoSQL document store
- Higher cost for high-volume operations

## Migration Between Storage Backends

To migrate from one storage backend to another:

1. Export data from current backend
2. Update `.env` with new backend configuration
3. Import data to new backend
4. Restart agents

**Note**: The system does not automatically migrate data between backends. You'll need to implement a migration script if needed.

## Troubleshooting

### PostgreSQL Issues

- **Connection refused**: Check PostgreSQL is running and connection string is correct
- **Authentication failed**: Verify username and password
- **Database does not exist**: Create database manually or ensure user has CREATE DATABASE permission
- **JSONB errors**: Ensure PostgreSQL version is 9.4 or higher

### Cosmos DB Issues

- **Authentication failed**: Verify endpoint and key are correct
- **Container not found**: Containers are created automatically on first use
- **Rate limiting**: Cosmos DB has request unit limits; consider increasing throughput

## Code Usage

The storage client is automatically selected based on configuration:

```python
from shared.storage_client import create_storage_client

# Automatically selects PostgreSQL or Cosmos DB based on config
storage_client = create_storage_client()

# Use the client
storage_client.save_state("agent-id", "state-id", {"data": "value"})
state = storage_client.get_state("agent-id", "state-id")
```

The storage client interface is the same regardless of backend, so your code doesn't need to change when switching between PostgreSQL and Cosmos DB.

