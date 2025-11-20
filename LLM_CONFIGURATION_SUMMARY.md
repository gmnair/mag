# LLM Configuration Externalization Summary

## Overview

All LLM configuration has been externalized to YAML files with support for multiple providers (OpenAI, Anthropic/Claude, Google/Gemini, DeepSeek, Azure OpenAI). A configuration loader tool extracts metadata and a factory creates the appropriate LLM instance.

## Changes Made

### 1. Created LLM Configuration System

**New Files**:
- `llm_config/llm_config.yaml` - External LLM configuration
- `llm_config/llm_config_loader.py` - Tool to extract configuration metadata
- `llm_config/llm_factory.py` - Factory to create LLM instances
- `llm_config/__init__.py` - Package exports
- `LLM_CONFIGURATION.md` - Complete documentation

### 2. Updated Code

**Modified Files**:
- `shared/deep_agent.py` - Uses LLM factory instead of hardcoded ChatOpenAI
- `config.py` - Added `LLM_CONFIG_FILE` configuration
- `requirements.txt` - Added `langchain-anthropic` and `langchain-google-genai`

## Architecture

### Design Pattern: Factory Pattern

```
LLMFactory
├── create_llm() - Main factory method
├── _create_openai_llm()
├── _create_anthropic_llm()
├── _create_google_llm()
├── _create_deepseek_llm()
└── _create_azure_openai_llm()
```

### Configuration Tool: LLMConfigLoader

- Extracts metadata from YAML
- Resolves environment variables
- Applies defaults and model overrides
- Validates provider configuration

## Supported Providers

1. **OpenAI** - GPT-4, GPT-3.5-turbo, etc.
2. **Anthropic** - Claude 3 Opus, Sonnet, Haiku
3. **Google** - Gemini Pro, Gemini Pro Vision
4. **DeepSeek** - DeepSeek Chat
5. **Azure OpenAI** - Azure-hosted OpenAI models

## Configuration Features

### 1. Environment Variable Resolution

```yaml
api_key: ${OPENAI_API_KEY}  # Resolved from environment
```

### 2. Default Values

```yaml
defaults:
  temperature: 0.3
  max_tokens: 2000
```

### 3. Model-Specific Overrides

```yaml
model_overrides:
  gpt-4:
    temperature: 0.2
    max_tokens: 4000
```

### 4. Provider Enable/Disable

```yaml
providers:
  openai:
    enabled: true
  anthropic:
    enabled: false
```

## Usage

### Basic Usage

```python
from llm_config import create_llm

# Use active provider from config
llm = create_llm()

# Use specific provider
llm = create_llm(provider_name="anthropic")

# Override parameters
llm = create_llm(model="gpt-4-turbo", temperature=0.5)
```

### Configuration Loader

```python
from llm_config import get_llm_config_loader

loader = get_llm_config_loader()
config = loader.get_active_provider_config()
```

## Migration

### Before

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### After

```python
from llm_config import create_llm

llm = create_llm()  # Automatically uses config
```

## Benefits

1. **Multi-Provider Support**: Easy switching between providers
2. **Externalized Configuration**: All settings in YAML
3. **Environment Variables**: Secure API key management
4. **Default Values**: Consistent settings across providers
5. **Model Overrides**: Fine-tune per model
6. **Easy Testing**: Switch providers without code changes
7. **Type Safety**: Factory ensures correct LLM type

## Configuration File

Edit `llm_config/llm_config.yaml`:

```yaml
active_provider: openai

providers:
  openai:
    enabled: true
    api_key: ${OPENAI_API_KEY}
    model: gpt-4
    temperature: 0.3
```

## Environment Variables

Set in `.env`:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
DEEPSEEK_API_KEY=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...
```

## Integration

Automatically integrated into:
- **DeepAgent** - Uses factory for LLM creation
- **SCAP Agent** - Uses DeepAgent's LLM

No code changes needed - just update YAML configuration.

## Error Handling

- Missing API key → Returns `None`, logs warning
- Provider not found → Raises `ValueError`
- Provider disabled → Raises `ValueError`
- Package not installed → Logs error, returns `None`

## Future Enhancements

1. **Provider Health Checks**: Monitor provider availability
2. **Automatic Fallback**: Fallback to backup provider
3. **Cost Tracking**: Track usage per provider
4. **A/B Testing**: Test different providers
5. **Rate Limiting**: Handle rate limits per provider

