# Deep Agent Pattern Implementation

This system implements the **Deep Agent pattern** with sense-perceive-plan-learn cycles, making agents more autonomous and intelligent using LLMs.

## Deep Agent Pattern

Each agent follows a cyclical workflow:

```
Sense → Perceive → Plan → Execute → Learn
```

### 1. Sense
- **Discovers tools**: Available tools for the agent (Cosmos DB, Service Bus, etc.)
- **Discovers agents**: Other agents in the system and their capabilities
- **Retrieves context**: Previous state and conversation history from Cosmos DB
- **Extracts goals**: Identifies objectives from the current task

### 2. Perceive
- **LLM Analysis**: Uses LLM to understand the current situation
- **Context Understanding**: Analyzes retrieved context and goals
- **Priority Assessment**: Determines priority and relevant information
- **Next Steps**: Suggests appropriate next actions

### 3. Plan
- **LLM Planning**: Uses LLM to create an execution plan
- **Step-by-step**: Breaks down tasks into actionable steps
- **Tool/Agent Selection**: Chooses appropriate tools or agents for each step
- **Expected Outcomes**: Defines what to expect from each step

### 4. Execute
- **Task Execution**: Performs the actual work (extract, evaluate, validate, etc.)
- **Tool Usage**: Utilizes discovered tools
- **Agent Communication**: Sends messages to other agents if needed
- **Result Collection**: Gathers execution results

### 5. Learn
- **Outcome Analysis**: Uses LLM to analyze execution results
- **Lessons Learned**: Extracts key insights
- **Context Updates**: Updates context for future reference
- **History Storage**: Saves learning to Cosmos DB for future retrieval

## A2A SDK Integration

The system uses **a2a-sdk** types for standardized communication:

- `Message`: A2A protocol message structure
- `Role`: Message role (USER/AGENT)
- `Part`: Message content parts
- `MessageSendParams`: Parameters for sending messages
- `MessageSendConfiguration`: Configuration for message sending

### Message Flow

```python
# Create A2A message
message = create_a2a_message(
    message_id="msg-123",
    role="agent",
    text="Task description",
    context_id="conv-123",
    task_id="task-123"
)

# Wrap for ASB communication
wrapper = A2AMessageWrapper(
    message=message,
    from_agent="orchestration-agent",
    to_agent="extractor-agent",
    payload={"case_id": "CASE-001", "file_path": "data.csv"}
)

# Send via Azure Service Bus
await asb_client.send_message(wrapper, agent_id)
```

## Agent Autonomy

Each agent is now more autonomous:

1. **Self-Discovery**: Agents discover available tools and other agents
2. **Context Awareness**: Agents retrieve and understand previous context
3. **Intelligent Planning**: LLM generates execution plans based on situation
4. **Adaptive Learning**: Agents learn from outcomes and update context
5. **Goal-Oriented**: Agents extract and pursue goals from tasks

## LLM Integration

LLMs are used for:

- **Perception**: Understanding the current situation
- **Planning**: Creating execution plans
- **Learning**: Analyzing outcomes and extracting lessons
- **Summarization**: Generating transaction summaries (SCAP agent)

### LLM Configuration

Set `OPENAI_API_KEY` in `.env`:

```bash
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4
```

If LLM is unavailable, agents fall back to rule-based behavior.

## Context History

All context is stored in Cosmos DB:

- **Conversation History**: All messages between agents
- **Task Details**: Execution details and results
- **Learning Insights**: Lessons learned from each execution
- **State Flow**: Workflow state at each step

Agents can retrieve previous context to:
- Understand previous interactions
- Learn from past experiences
- Maintain continuity across sessions
- Improve decision-making over time

## Example: Extractor Agent Deep Cycle

1. **Sense**: Discovers file reading tools, finds extractor capabilities, retrieves case context
2. **Perceive**: LLM understands "need to extract transactions from CSV file for case CASE-001"
3. **Plan**: LLM creates plan: "Read file → Parse CSV → Validate data → Store in Cosmos DB → Notify evaluator"
4. **Execute**: Performs extraction, stores transactions, sends message to evaluator
5. **Learn**: LLM analyzes: "Successfully extracted 100 transactions. File format was standard CSV. No errors encountered."

## Benefits

1. **Autonomy**: Agents make decisions based on context and goals
2. **Intelligence**: LLM provides reasoning and planning capabilities
3. **Learning**: Agents improve over time by learning from outcomes
4. **Adaptability**: Agents adapt to different situations
5. **Context Awareness**: Agents maintain awareness of previous interactions

## Configuration

Deep Agent behavior can be configured:

```python
# In agent initialization
agent = ExtractorAgent(
    agent_id="extractor-agent",
    asb_client=asb_client,
    cosmos_client=cosmos_client,
    state_manager=state_manager,
    llm_model="gpt-4"  # Optional: specify LLM model
)
```

## Monitoring

Monitor Deep Agent cycles:

- Check `agent_tasks` container for execution plans
- Review `conversations` container for perception and learning insights
- Examine `agent_states` for workflow progression

Each task includes:
- `perception`: LLM's understanding of the situation
- `plan`: Generated execution plan
- `learning`: Lessons learned from execution

