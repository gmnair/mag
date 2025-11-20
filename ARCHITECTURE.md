# Architecture Documentation

## System Overview

The multi-agent transaction review system implements a distributed architecture where agents communicate asynchronously using the A2A Protocol over Azure Service Bus. Each agent is independently deployable and maintains its own state in Azure Cosmos DB.

## A2A Protocol Implementation

The system implements the A2A Protocol specification for agent-to-agent communication:

### Message Structure

```python
{
    "from_agent": "orchestration-agent",
    "to_agent": "extractor-agent",
    "message_type": "task",
    "payload": {
        "case_id": "CASE-001",
        "file_path": "/path/to/file.csv",
        "action": "extract_transactions"
    },
    "metadata": {
        "agent_id": "orchestration-agent",
        "agent_type": "orchestration",
        "task_id": "task-123",
        "case_id": "CASE-001",
        "timestamp": "2024-01-01T00:00:00Z"
    },
    "conversation_id": "conv-123",
    "correlation_id": "corr-123"
}
```

### Message Routing

- Messages are sent to Azure Service Bus topic
- Each agent has its own subscription
- Messages are filtered by `to_agent` field
- Agents process messages intended for them based on the `to` field

## Agent Communication Flow

```
┌─────────────────┐
│   API Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Orchestration Agent │
│   (A2A API)        │
└────────┬────────────┘
         │ A2A Message
         ▼
┌─────────────────────┐
│  Extractor Agent    │
│  (ASB Topic)        │
└────────┬────────────┘
         │ A2A Message
         ▼
┌─────────────────────┐
│  Evaluator Agent    │
│  (ASB Topic)        │
└────────┬────────────┘
         │ A2A Message
         ▼
┌─────────────────────┐
│    SCAP Agent       │
│  (ASB Topic)        │
└─────────────────────┘
```

## State Management

### LangGraph Workflow

The system uses LangGraph to define the workflow state machine:

```python
orchestration → extraction → evaluation → scap → END
```

### State Persistence

State is persisted in Cosmos DB with the following structure:

- **Container**: `agent_states`
- **Key**: `{agent_id}_{state_id}`
- **Fields**: All state fields from `TransactionReviewState`

### State Retrieval

Any instance of an agent can retrieve previous state using:
- `agent_id`: Identifies which agent's state
- `state_id`: Usually `conversation_id` or `case_id`

## Data Storage

### Cosmos DB Containers

1. **agent_states**: Workflow state for each agent instance
2. **agent_tasks**: Task details and execution results
3. **conversations**: Complete conversation history across agents
4. **transactions**: Extracted transaction data

### Data Access Patterns

- **State**: Retrieved by `agent_id` + `state_id`
- **Tasks**: Retrieved by `agent_id` + `task_id`
- **Conversations**: Retrieved by `conversation_id`
- **Transactions**: Retrieved by `case_id`

## Agent Responsibilities

### Orchestration Agent

- Exposes REST API (FastAPI)
- Receives transaction review requests
- Creates initial workflow state
- Sends task message to Extractor Agent
- Provides status endpoint

### Extractor Agent

- Receives file path from Orchestration Agent
- Extracts transactions from file (CSV, JSON, Excel)
- Stores transactions in Cosmos DB
- Updates workflow state
- Sends task message to Evaluator Agent

### Evaluator Agent

- Receives transactions from Extractor Agent
- Delegates validation to SCAP Agent
- Updates workflow state
- Acts as coordinator for sub-agents

### SCAP Agent

- Receives transactions from Evaluator Agent
- Validates against externalizable rules (YAML)
- Flags risks based on:
  - Sensitive countries
  - Sensitive jurisdictions
  - Amount thresholds
- Generates summary using LLM (with fallback)
- Updates final workflow state

## Rule Engine

### Configuration

Rules are externalized in `scap_rules.yaml`:

```yaml
sensitive_countries:
  - "IR"
  - "KP"
  - "SY"

sensitive_jurisdictions:
  - "OFFSHORE"
  - "TAX_HAVEN"

risk_threshold: 1000.0
```

### Rule Evaluation

Each transaction is evaluated against:
1. Country sensitivity check
2. Jurisdiction sensitivity check
3. Amount threshold check

Transaction is flagged if:
- (Sensitive country OR Sensitive jurisdiction) AND Amount > threshold

## Error Handling

### Message Processing Errors

- Errors are logged
- Error responses sent back to originating agent
- Failed messages go to dead-letter queue

### State Recovery

- Agents can retrieve previous state on restart
- Task details stored for audit trail
- Conversation history preserved for context

## Scalability

### Horizontal Scaling

- Each agent can run multiple instances
- Azure Service Bus handles message distribution
- Cosmos DB supports concurrent reads/writes

### State Isolation

- Each workflow instance has unique `conversation_id`
- State is partitioned by agent and conversation
- No shared state between workflow instances

## Security Considerations

1. **Message Encryption**: Azure Service Bus supports encryption in transit
2. **Data Encryption**: Cosmos DB supports encryption at rest
3. **Access Control**: Use Azure RBAC for service access
4. **API Security**: Implement authentication for orchestration API
5. **Secrets Management**: Use Azure Key Vault for credentials

## Monitoring

### Key Metrics

- Message throughput per agent
- State persistence success rate
- Task completion time
- Error rates
- LLM API usage (SCAP agent)

### Logging

- All agents log to stdout
- Structured logging with agent_id, task_id, case_id
- Error logging with stack traces

## Future Enhancements

1. **Retry Logic**: Automatic retry for failed tasks
2. **Circuit Breaker**: Prevent cascade failures
3. **Rate Limiting**: Control message processing rate
4. **Dead Letter Handling**: Automatic retry of failed messages
5. **Metrics Export**: Prometheus/Application Insights integration
6. **Distributed Tracing**: Track requests across agents

