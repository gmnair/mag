# Quick Start Guide

## Prerequisites Setup

1. **Azure Service Bus**:
   ```bash
   # Create Service Bus namespace and topic in Azure Portal
   # Get connection string from Shared Access Policies
   ```

2. **Azure Cosmos DB**:
   ```bash
   # Create Cosmos DB account in Azure Portal
   # Get endpoint and key from Connection String
   ```

3. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Azure credentials
   ```

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Running the System

### Terminal 1: Orchestration Agent
```bash
python main.py orchestration
```
This starts the API server on `http://localhost:8000`

### Terminal 2: Extractor Agent
```bash
python main.py extractor
```

### Terminal 3: Evaluator Agent
```bash
python main.py evaluator
```

### Terminal 4: SCAP Agent
```bash
python main.py scap
```

## Testing

### Option 1: Using curl

```bash
# Trigger transaction review
curl -X POST http://localhost:8000/api/v1/transaction-review \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "CASE-001",
    "file_path": "example_transactions.csv"
  }'

# Check status
curl http://localhost:8000/api/v1/status/CASE-001
```

### Option 2: Using test client

```bash
python test_client.py CASE-001 example_transactions.csv
```

## Expected Workflow

1. **API Request** → Orchestration Agent receives request
2. **State Created** → Initial state stored in Cosmos DB
3. **Message Sent** → Orchestration sends message to Extractor via ASB
4. **Extraction** → Extractor processes file and stores transactions
5. **Message Sent** → Extractor sends message to Evaluator
6. **Delegation** → Evaluator sends message to SCAP
7. **Validation** → SCAP validates transactions against rules
8. **Summary** → SCAP generates summary (LLM or fallback)
9. **State Updated** → Final state stored with results

## Verifying Results

### Check Cosmos DB

1. Navigate to Azure Portal → Cosmos DB
2. Open Data Explorer
3. Check containers:
   - `agent_states` - workflow states
   - `agent_tasks` - task execution details
   - `conversations` - message history
   - `transactions` - extracted transaction data

### Check Logs

Each agent logs to stdout. Look for:
- Message received/sent confirmations
- State save/load operations
- Task completion status
- Error messages (if any)

## Troubleshooting

### Agents not receiving messages
- Verify ASB connection string
- Check topic exists: `a2a-messages`
- Verify agent IDs match in config

### State not persisting
- Verify Cosmos DB connection
- Check database name: `transaction_review`
- Verify containers are created

### LLM summaries not working
- Check OpenAI API key in `.env`
- System will use fallback summary if LLM unavailable

## Next Steps

- Customize `scap_rules.yaml` for your compliance requirements
- Add authentication to orchestration API
- Set up monitoring and alerting
- Deploy to production (see DEPLOYMENT.md)

