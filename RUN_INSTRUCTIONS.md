# Running the Multi-Agent System

## Current Status

The orchestration agent has been started in the background. However, to run the complete system, you need:

## Prerequisites

1. **Azure Service Bus** - Connection string and topic
2. **Azure Cosmos DB** - Endpoint and key
3. **OpenAI API Key** (optional, for LLM features)

## Setup Configuration

Create a `.env` file in the project root with:

```bash
# Azure Service Bus
ASB_CONNECTION_STRING=Endpoint=sb://your-namespace.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=your-key
ASB_TOPIC_NAME=a2a-messages

# Azure Cosmos DB
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key
COSMOS_DATABASE_NAME=transaction_review

# OpenAI (optional)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4
```

## Running All Agents

You need to run each agent in a separate terminal/process:

### Terminal 1: Orchestration Agent (API Server)
```bash
.venv\Scripts\python.exe main.py orchestration
```
This starts the API server on `http://localhost:8000`

### Terminal 2: Extractor Agent
```bash
.venv\Scripts\python.exe main.py extractor
```

### Terminal 3: Evaluator Agent
```bash
.venv\Scripts\python.exe main.py evaluator
```

### Terminal 4: SCAP Agent
```bash
.venv\Scripts\python.exe main.py scap
```

## Testing the System

Once all agents are running, test with:

```bash
curl -X POST http://localhost:8000/api/v1/transaction-review ^
  -H "Content-Type: application/json" ^
  -d "{\"case_id\": \"CASE-001\", \"file_path\": \"example_transactions.csv\"}"
```

Or use the test client:
```bash
.venv\Scripts\python.exe test_client.py CASE-001 example_transactions.csv
```

## API Endpoints

- `POST /api/v1/transaction-review` - Trigger transaction review workflow
- `GET /api/v1/status/{case_id}` - Check workflow status
- `GET /docs` - API documentation (Swagger UI)

## Troubleshooting

1. **Agents not receiving messages**: Check Azure Service Bus connection string
2. **State not persisting**: Verify Cosmos DB configuration
3. **LLM not working**: Check OpenAI API key (system will use fallback if unavailable)
4. **Port already in use**: Change `A2A_API_PORT` in `.env` or config.py

## Note

The orchestration agent is currently running in the background. You can check if it's working by visiting:
- http://localhost:8000/docs (API documentation)
- http://localhost:8000/api/v1/status/CASE-001 (status endpoint)

If you see errors, check the console output for configuration issues.

