# Prompt Template System

## Overview

All prompts in the system are externalized to configuration files and managed through a **Template Method design pattern**. This allows for easy customization, versioning, and A/B testing of prompts without code changes.

## Architecture

### Design Pattern: Template Method

The prompt system uses the **Template Method pattern** with the following components:

1. **PromptTemplate (Abstract Base Class)**: Defines the interface for all prompt templates
2. **Concrete Template Classes**: Specific implementations for each prompt type
3. **PromptTemplateManager**: Manages template loading and rendering
4. **YAML Configuration**: External prompt definitions

### Class Hierarchy

```
PromptTemplate (ABC)
├── DeepAgentPerceptionTemplate
├── DeepAgentPlanningTemplate
├── DeepAgentLearningTemplate
└── SCAPAnalysisTemplate
```

## Template Structure

Each template includes:

- **Template String**: The prompt text with variable placeholders (using `${variable}` syntax)
- **System Message**: Optional system message for LLM context
- **Variable Formatting**: Methods to format variables before substitution

## Configuration

### YAML Configuration File

Prompts are defined in `prompts/prompts.yaml`:

```yaml
templates:
  deep_agent_perception:
    enabled: true
    system_message: "You are an intelligent agent..."
    template: |
      You are an intelligent agent analyzing a situation...
      Context: ${context}
      Goals: ${goals}
```

### Environment Variable

You can specify a custom prompts file:

```bash
PROMPTS_CONFIG_FILE=prompts/custom_prompts.yaml
```

## Usage

### Basic Usage

```python
from prompts import get_template_manager

template_manager = get_template_manager()

# Render a template
prompt = template_manager.render_template(
    "deep_agent_perception",
    context="...",
    goals=["goal1", "goal2"],
    tool_count=5,
    agent_count=3
)

# Get system message
system_message = template_manager.get_system_message("deep_agent_perception")
```

### In Code

The system automatically uses templates in:

- **Deep Agent Perception**: `shared/deep_agent.py` - `_perceive_node()`
- **Deep Agent Planning**: `shared/deep_agent.py` - `_plan_node()`
- **Deep Agent Learning**: `shared/deep_agent.py` - `_learn_node()`
- **SCAP Analysis**: `agents/scap_agent.py` - `_generate_summary()`

## Available Templates

### 1. deep_agent_perception

**Purpose**: Analyze situation and provide perception

**Variables**:
- `context`: Formatted context string
- `goals`: List of agent goals
- `tool_count`: Number of available tools
- `agent_count`: Number of available agents

**System Message**: "You are an intelligent agent capable of analyzing complex situations..."

### 2. deep_agent_planning

**Purpose**: Create execution plan based on perception

**Variables**:
- `perception`: Understanding from perception phase
- `goals`: List of agent goals
- `tools`: List of available tools
- `agents`: List of available agents

**System Message**: "You are a strategic planning agent..."

### 3. deep_agent_learning

**Purpose**: Analyze outcomes and extract insights

**Variables**:
- `plan`: Execution plan that was followed
- `execution_results`: Results from plan execution

**System Message**: "You are a learning agent..."

### 4. scap_analysis

**Purpose**: Analyze flagged transactions and provide summary

**Variables**:
- `case_id`: Case identifier
- `flagged_transactions`: Formatted list of flagged transactions

**System Message**: "You are a financial compliance analyst..."

## Customization

### Method 1: Edit YAML File

Edit `prompts/prompts.yaml` directly:

```yaml
templates:
  deep_agent_perception:
    enabled: true
    system_message: "Your custom system message"
    template: |
      Your custom prompt template
      Context: ${context}
      ...
```

### Method 2: Create Custom Template Class

```python
from prompts.prompt_templates import PromptTemplate

class CustomTemplate(PromptTemplate):
    def __init__(self):
        super().__init__(
            template_string="Your template with ${variables}"
        )
    
    def get_system_message(self):
        return "Your system message"
    
    def format_variables(self, **kwargs):
        # Custom formatting logic
        return kwargs
```

### Method 3: Disable Template

Set `enabled: false` in YAML:

```yaml
templates:
  deep_agent_perception:
    enabled: false  # This template will not be loaded
```

## Variable Substitution

Templates use Python's `string.Template` for variable substitution:

- `${variable}` - Required variable (will show as-is if missing)
- Safe substitution - Missing variables don't cause errors

### Example

```python
template = Template("Hello ${name}, you have ${count} messages")
result = template.safe_substitute(name="Alice", count=5)
# Result: "Hello Alice, you have 5 messages"
```

## Best Practices

1. **Keep Prompts Focused**: Each template should have a single, clear purpose
2. **Use System Messages**: Provide context via system messages for better LLM responses
3. **Document Variables**: Document all variables in YAML comments
4. **Version Control**: Keep prompts.yaml in version control
5. **Test Changes**: Test prompt changes before deploying
6. **A/B Testing**: Use different config files for A/B testing

## Advanced Features

### Dynamic Template Loading

Templates are loaded on first access and cached:

```python
# First call loads from YAML
manager = get_template_manager()

# Subsequent calls use cached instance
manager2 = get_template_manager()  # Same instance
```

### Template Validation

Templates are validated on load:
- Missing required variables are logged as warnings
- Invalid YAML causes fallback to default templates

### Fallback Behavior

If a template is not found or fails to load:
- System falls back to hardcoded default templates
- Errors are logged but don't break the system

## Migration Guide

### From Hardcoded Prompts

**Before**:
```python
prompt = f"""Analyze the situation...
Context: {context}
Goals: {goals}
"""
```

**After**:
```python
from prompts import get_template_manager

manager = get_template_manager()
prompt = manager.render_template(
    "deep_agent_perception",
    context=context,
    goals=goals,
    tool_count=len(tools),
    agent_count=len(agents)
)
```

## Troubleshooting

### Template Not Found

**Error**: `Template 'xxx' not found`

**Solution**: Check template name in `prompts.yaml` matches the code

### Variable Not Substituted

**Issue**: Variables show as `${variable}` in output

**Solution**: Ensure variable is passed to `render_template()`

### YAML Parse Error

**Error**: YAML syntax errors

**Solution**: Validate YAML syntax using a YAML validator

## Examples

See `prompts/prompts.yaml` for complete examples of all templates.

