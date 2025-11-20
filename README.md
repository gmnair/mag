# Multi-Agent Transaction Review System

A multi-agent system for transaction review using the A2A Protocol, Azure Service Bus, and Azure Cosmos DB. This system implements a distributed agent architecture where agents communicate via A2A messages through Azure Service Bus.

## Architecture

The system consists of four independently deployed agents:

1. **Orchestration Agent**: Root agent that exposes A2A API to trigger agentic workflows
2. **Extractor Agent**: Helper agent responsible for extracting transactions from input files and storing them in Cosmos DB
3. **Evaluator Agent**: Helper agent that delegates to downstream sub-agents for transaction validation
4. **SCAP Agent**: Sub-agent specialized in identifying sensitive countries and flagging risks based on configurable rules

## Features

- **A2A Protocol Communication**: Agents communicate using the A2A protocol via Azure Service Bus
- **State Management**: LangGraph-based state management with Cosmos DB persistence
- **Task Tracking**: All tasks are stored in Cosmos DB for retrieval across agent instances
- **Conversation History**: Complete conversation history stored in Cosmos DB for context retrieval
- **Rule Engine**: Externalizable rules for SCAP agent (YAML-based)
- **LLM Integration**: SCAP agent uses LLM for generating transaction summaries

## Prerequisites

- Python 3.8+
- Azure Service Bus namespace with a topic
- **Storage Backend** (choose one):
  - PostgreSQL (9.4+) OR
  - Azure Cosmos DB account
- **LLM Provider** (optional, for AI features):
  - OpenAI, Anthropic (Claude), Google (Gemini), DeepSeek, or Azure OpenAI
  - API key for chosen provider

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mag
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Azure and OpenAI credentials
```

4. Configure SCAP rules (optional):
```bash
# Edit scap_rules.yaml to customize sensitive countries and thresholds
```

## Configuration

### Environment Variables

**Storage Configuration** (choose one):
- `POSTGRES_CONNECTION_STRING`: PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/db`)
- OR
- `COSMOS_ENDPOINT`: Azure Cosmos DB endpoint
- `COSMOS_KEY`: Azure Cosmos DB key
- `COSMOS_DATABASE_NAME`: Cosmos DB database name (default: "transaction_review")

**LLM Configuration**:
- Configure in `llm_config/llm_config.yaml`
- Set API keys in environment variables (see LLM_CONFIGURATION.md)
- Supports: OpenAI, Anthropic, Google, DeepSeek, Azure OpenAI

**Other Configuration**:
- `ASB_CONNECTION_STRING`: Azure Service Bus connection string
- `ASB_TOPIC_NAME`: Azure Service Bus topic name (default: "a2a-messages")
- `SCAP_RULE_THRESHOLD`: Risk threshold amount (default: 1000.0)

### SCAP Rules

Edit `scap_rules.yaml` to configure:
- Sensitive countries list
- Sensitive jurisdictions list
- Risk threshold amount

## Usage

### Running Agents

Each agent runs independently. Start each agent in a separate terminal/process:

**Orchestration Agent** (with API server):
```bash
python main.py orchestration
```

**Extractor Agent**:
```bash
python main.py extractor
```

**Evaluator Agent**:
```bash
python main.py evaluator
```

**SCAP Agent**:
```bash
python main.py scap
```

### API Usage

Once the orchestration agent is running, you can trigger a transaction review workflow:

```bash
curl -X POST http://localhost:8000/api/v1/transaction-review \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "CASE-001",
    "file_path": "/path/to/transactions.csv"
  }'
```

Check workflow status:
```bash
curl http://localhost:8000/api/v1/status/CASE-001
```

### Transaction File Format

The system supports CSV, JSON, and Excel files. Required fields:
- `transaction_id` (or auto-generated)
- `account`
- `country`
- `jurisdiction`
- `amount`

Example CSV:
```csv
transaction_id,account,country,jurisdiction,amount
TXN-001,ACC-123,US,US,500
TXN-002,ACC-456,IR,IR,1500
TXN-003,ACC-789,CN,CN,800
```

## Workflow

1. **Orchestration Agent** receives API request with case_id and file_path
2. **Orchestration Agent** creates initial state and sends message to **Extractor Agent**
3. **Extractor Agent** extracts transactions from file and stores in Cosmos DB
4. **Extractor Agent** sends message to **Evaluator Agent**
5. **Evaluator Agent** delegates to **SCAP Agent**
6. **SCAP Agent** validates transactions against rules and generates summary
7. **SCAP Agent** updates final state with results

## A2A Protocol

The system follows the A2A protocol specification:
- Messages include `from_agent`, `to_agent`, `message_type`, `payload`, and `metadata`
- Agent metadata includes `agent_id`, `agent_type`, `task_id`, and `case_id`
- Messages are routed via Azure Service Bus using the `to_agent` field
- Each agent processes messages intended for it based on the `to` field

## State Management

- **State Flow**: Stored in Cosmos DB container `agent_states`
- **Task Details**: Stored in Cosmos DB container `agent_tasks`
- **Conversations**: Stored in Cosmos DB container `conversations`
- **Transactions**: Stored in Cosmos DB container `transactions`

All state is keyed by agent_id and state_id/task_id for retrieval across agent instances.

## Development

### Project Structure

```
mag/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── orchestration_agent.py
│   ├── extractor_agent.py
│   ├── evaluator_agent.py
│   └── scap_agent.py
├── shared/
│   ├── __init__.py
│   ├── a2a_message.py
│   ├── asb_client.py
│   ├── cosmos_client.py
│   └── state_manager.py
├── config.py
├── main.py
├── scap_rules.yaml
├── requirements.txt
└── README.md
```

## License

[Your License Here]

