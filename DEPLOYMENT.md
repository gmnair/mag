# Deployment Guide

This guide explains how to deploy the multi-agent transaction review system.

## Prerequisites

1. **Azure Account** with:
   - Azure Service Bus namespace
   - Azure Cosmos DB account
   
2. **Python 3.8+** installed

3. **OpenAI API Key** (optional, for LLM summaries)

## Azure Setup

### 1. Azure Service Bus Setup

1. Create a Service Bus namespace in Azure Portal
2. Create a topic named `a2a-messages` (or update `ASB_TOPIC_NAME` in config)
3. Get the connection string from Shared Access Policies
4. Update `.env` with `ASB_CONNECTION_STRING`

### 2. Azure Cosmos DB Setup

1. Create a Cosmos DB account in Azure Portal
2. Create a database (or use existing)
3. The system will automatically create the following containers:
   - `agent_states` - for state flow storage
   - `agent_tasks` - for task details
   - `conversations` - for conversation history
   - `transactions` - for transaction data
4. Get the endpoint and key from Connection String
5. Update `.env` with `COSMOS_ENDPOINT` and `COSMOS_KEY`

## Local Deployment

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

### Step 3: Configure SCAP Rules (Optional)

Edit `scap_rules.yaml` to customize:
- Sensitive countries
- Sensitive jurisdictions
- Risk threshold

### Step 4: Start Agents

Each agent runs independently. Open separate terminals for each:

**Terminal 1 - Orchestration Agent:**
```bash
python main.py orchestration
```

**Terminal 2 - Extractor Agent:**
```bash
python main.py extractor
```

**Terminal 3 - Evaluator Agent:**
```bash
python main.py evaluator
```

**Terminal 4 - SCAP Agent:**
```bash
python main.py scap
```

## Docker Deployment

### Create Dockerfile for Each Agent

Example Dockerfile:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py", "orchestration"]
```

### Build and Run

```bash
# Build images
docker build -t orchestration-agent -f Dockerfile.orchestration .
docker build -t extractor-agent -f Dockerfile.extractor .
docker build -t evaluator-agent -f Dockerfile.evaluator .
docker build -t scap-agent -f Dockerfile.scap .

# Run containers
docker run -d --env-file .env orchestration-agent
docker run -d --env-file .env extractor-agent
docker run -d --env-file .env evaluator-agent
docker run -d --env-file .env scap-agent
```

## Azure Container Instances Deployment

### 1. Build and Push Images to Azure Container Registry

```bash
# Login to Azure
az login

# Create resource group
az group create --name transaction-review-rg --location eastus

# Create container registry
az acr create --resource-group transaction-review-rg --name transactionreview --sku Basic

# Login to ACR
az acr login --name transactionreview

# Build and push images
az acr build --registry transactionreview --image orchestration-agent:latest .
az acr build --registry transactionreview --image extractor-agent:latest .
az acr build --registry transactionreview --image evaluator-agent:latest .
az acr build --registry transactionreview --image scap-agent:latest .
```

### 2. Deploy to Azure Container Instances

```bash
# Deploy orchestration agent
az container create \
  --resource-group transaction-review-rg \
  --name orchestration-agent \
  --image transactionreview.azurecr.io/orchestration-agent:latest \
  --registry-login-server transactionreview.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --environment-variables-file .env \
  --ports 8000 \
  --dns-name-label orchestration-agent

# Deploy extractor agent
az container create \
  --resource-group transaction-review-rg \
  --name extractor-agent \
  --image transactionreview.azurecr.io/extractor-agent:latest \
  --registry-login-server transactionreview.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --environment-variables-file .env

# Deploy evaluator agent
az container create \
  --resource-group transaction-review-rg \
  --name evaluator-agent \
  --image transactionreview.azurecr.io/evaluator-agent:latest \
  --registry-login-server transactionreview.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --environment-variables-file .env

# Deploy SCAP agent
az container create \
  --resource-group transaction-review-rg \
  --name scap-agent \
  --image transactionreview.azurecr.io/scap-agent:latest \
  --registry-login-server transactionreview.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --environment-variables-file .env
```

## Kubernetes Deployment

### 1. Create Kubernetes Manifests

Create `k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestration-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: orchestration-agent
  template:
    metadata:
      labels:
        app: orchestration-agent
    spec:
      containers:
      - name: orchestration-agent
        image: transactionreview.azurecr.io/orchestration-agent:latest
        envFrom:
        - secretRef:
            name: agent-secrets
        ports:
        - containerPort: 8000
---
apiVersion: v1
kind: Service
metadata:
  name: orchestration-agent-service
spec:
  selector:
    app: orchestration-agent
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 2. Deploy to Kubernetes

```bash
# Create secrets
kubectl create secret generic agent-secrets --from-env-file=.env

# Deploy
kubectl apply -f k8s/
```

## Testing

### 1. Test API Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/transaction-review \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "CASE-001",
    "file_path": "example_transactions.csv"
  }'
```

### 2. Check Status

```bash
curl http://localhost:8000/api/v1/status/CASE-001
```

### 3. Use Test Client

```bash
python test_client.py CASE-001 example_transactions.csv
```

## Monitoring

### Azure Service Bus Metrics

Monitor message throughput, dead-letter queue, and subscription metrics in Azure Portal.

### Azure Cosmos DB Metrics

Monitor request units, storage, and latency in Azure Portal.

### Application Logs

Each agent logs to stdout. For production, configure log aggregation:
- Azure Log Analytics
- Application Insights
- ELK Stack

## Troubleshooting

### Agents Not Receiving Messages

1. Verify Azure Service Bus connection string
2. Check topic and subscription exist
3. Verify agent IDs match in configuration
4. Check message routing (to_agent field)

### State Not Persisting

1. Verify Cosmos DB connection
2. Check database and container names
3. Verify partition keys are correct

### LLM Summaries Not Working

1. Verify OpenAI API key is set
2. Check API quota and limits
3. System will fall back to rule-based summary if LLM fails

## Scaling

### Horizontal Scaling

Each agent can be scaled independently:
- Orchestration: Scale based on API load
- Extractor: Scale based on file processing load
- Evaluator: Scale based on transaction volume
- SCAP: Scale based on validation load

### Vertical Scaling

Increase container resources for CPU/memory intensive operations (e.g., LLM processing in SCAP agent).

## Security

1. **Secrets Management**: Use Azure Key Vault for sensitive credentials
2. **Network Security**: Use private endpoints for Azure services
3. **Authentication**: Implement API authentication for orchestration agent
4. **Encryption**: Enable encryption at rest for Cosmos DB
5. **Access Control**: Use RBAC for Azure resources

