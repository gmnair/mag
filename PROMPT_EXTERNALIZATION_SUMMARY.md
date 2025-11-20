# Prompt Externalization Summary

## Overview

All prompts have been externalized to configuration files and managed through a **Template Method design pattern**. This enables easy customization, versioning, and A/B testing without code changes.

## Changes Made

### 1. Created Prompt Template System

**New Files**:
- `prompts/prompt_templates.py` - Template system implementation
- `prompts/prompts.yaml` - External prompt configuration
- `prompts/__init__.py` - Package exports
- `PROMPT_TEMPLATES.md` - Documentation

### 2. Updated Code to Use Templates

**Modified Files**:
- `shared/deep_agent.py` - Uses templates for perception, planning, and learning
- `agents/scap_agent.py` - Uses template for transaction analysis
- `config.py` - Added `PROMPTS_CONFIG_FILE` configuration

## Template Design Pattern

### Architecture

```
PromptTemplate (ABC)
├── render() - Template method for rendering
├── get_system_message() - Abstract method
└── format_variables() - Hook method for variable formatting

Concrete Implementations:
├── DeepAgentPerceptionTemplate
├── DeepAgentPlanningTemplate
├── DeepAgentLearningTemplate
└── SCAPAnalysisTemplate
```

### Key Features

1. **Template Method Pattern**: Abstract base class defines the algorithm structure
2. **Variable Substitution**: Uses Python's `string.Template` for safe substitution
3. **System Messages**: Each template can provide a system message for LLM context
4. **YAML Configuration**: External configuration for easy customization
5. **Fallback Support**: Default templates if YAML loading fails

## Prompts Externalized

### 1. Deep Agent Perception
- **Location**: `shared/deep_agent.py` - `_perceive_node()`
- **Template**: `deep_agent_perception`
- **Variables**: context, goals, tool_count, agent_count

### 2. Deep Agent Planning
- **Location**: `shared/deep_agent.py` - `_plan_node()`
- **Template**: `deep_agent_planning`
- **Variables**: perception, goals, tools, agents

### 3. Deep Agent Learning
- **Location**: `shared/deep_agent.py` - `_learn_node()`
- **Template**: `deep_agent_learning`
- **Variables**: plan, execution_results

### 4. SCAP Analysis
- **Location**: `agents/scap_agent.py` - `_generate_summary()`
- **Template**: `scap_analysis`
- **Variables**: case_id, flagged_transactions

## Usage

### Customizing Prompts

Edit `prompts/prompts.yaml`:

```yaml
templates:
  deep_agent_perception:
    enabled: true
    system_message: "Your custom system message"
    template: |
      Your custom prompt
      Context: ${context}
      Goals: ${goals}
```

### Using Templates in Code

```python
from prompts import get_template_manager

manager = get_template_manager()
prompt = manager.render_template(
    "deep_agent_perception",
    context="...",
    goals=["goal1", "goal2"],
    tool_count=5,
    agent_count=3
)
```

## Benefits

1. **Separation of Concerns**: Prompts separated from business logic
2. **Easy Customization**: Change prompts without code changes
3. **Version Control**: Track prompt changes in Git
4. **A/B Testing**: Use different config files for testing
5. **Maintainability**: Centralized prompt management
6. **Reusability**: Templates can be reused across agents
7. **Type Safety**: Template classes provide structure

## Configuration

### Environment Variable

```bash
PROMPTS_CONFIG_FILE=prompts/custom_prompts.yaml
```

### Default Location

If not specified, uses: `prompts/prompts.yaml`

## Migration Notes

- All hardcoded prompts have been replaced
- System messages are now included in templates
- Variable formatting is handled by template classes
- Backward compatible - defaults work if YAML fails

## Testing

To test prompt changes:

1. Edit `prompts/prompts.yaml`
2. Restart agents
3. Test with actual workflows
4. Compare results

## Future Enhancements

1. **Prompt Versioning**: Track prompt versions
2. **A/B Testing Framework**: Built-in A/B testing
3. **Prompt Analytics**: Track prompt performance
4. **Multi-language Support**: Templates for different languages
5. **Prompt Validation**: Validate prompts before use

