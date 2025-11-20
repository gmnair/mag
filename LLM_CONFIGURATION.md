# LLM Configuration System

## Overview

The LLM configuration system externalizes all LLM settings to YAML files and supports multiple LLM providers (OpenAI, Anthropic/Claude, Google/Gemini, DeepSeek, Azure OpenAI). A configuration loader tool extracts metadata from YAML and a factory creates the appropriate LLM instance.

## Architecture

### Components

1. **LLMConfigLoader** - Tool that extracts LLM configuration metadata from YAML
2. **LLMFactory** - Factory pattern to create LLM instances based on configuration
3. **llm_config.yaml** - External configuration file with all LLM settings

### Design Pattern: Factory Pattern

The system uses the **Factory Pattern** to create LLM instances:
- Single factory interface (`LLMFactory`)
- Provider-specific creation methods
- Configuration-driven instantiation

## Configuration File

### Location

Default: `llm_config/llm_config.yaml`

Can be overridden with environment variable:
```bash
LLM_CONFIG_FILE=path/to/custom_llm_config.yaml
```

### Structure

```yaml
active_provider: openai  # Active provider to use

providers:
  openai:
    enabled: true
    api_key: ${OPENAI_API_KEY}
    model: gpt-4
    temperature: 0.3
    # ... other settings
  
  anthropic:
    enabled: false
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-opus-20240229
    # ... other settings

defaults:
  temperature: 0.3
  max_tokens: 2000
  # ... default settings
```

## Supported Providers

### 1. OpenAI

```yaml
openai:
  enabled: true
  api_key: ${OPENAI_API_KEY}
  model: gpt-4
  temperature: 0.3
  max_tokens: 2000
  base_url: null  # Optional: for custom endpoints
  organization: null  # Optional: OpenAI organization ID
```

**Required Package**: `langchain-openai`

### 2. Anthropic (Claude)

```yaml
anthropic:
  enabled: true
  api_key: ${ANTHROPIC_API_KEY}
  model: claude-3-opus-20240229
  temperature: 0.3
  max_tokens: 2000
```

**Required Package**: `langchain-anthropic`

**Available Models**:
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

### 3. Google (Gemini)

```yaml
google:
  enabled: true
  api_key: ${GOOGLE_API_KEY}
  model: gemini-pro
  temperature: 0.3
  max_tokens: 2000
  location: us-central1  # Optional: for Vertex AI
```

**Required Package**: `langchain-google-genai`

**Available Models**:
- `gemini-pro`
- `gemini-pro-vision`

### 4. DeepSeek

```yaml
deepseek:
  enabled: true
  api_key: ${DEEPSEEK_API_KEY}
  model: deepseek-chat
  temperature: 0.3
  max_tokens: 2000
  base_url: https://api.deepseek.com
```

**Required Package**: `langchain-openai` (uses OpenAI-compatible API)

### 5. Azure OpenAI

```yaml
azure_openai:
  enabled: true
  api_key: ${AZURE_OPENAI_API_KEY}
  model: gpt-4
  azure_endpoint: ${AZURE_OPENAI_ENDPOINT}
  api_version: 2024-02-15-preview
  deployment_name: gpt-4
  temperature: 0.3
  max_tokens: 2000
```

**Required Package**: `langchain-openai`

## Usage

### Basic Usage

```python
from llm_config import create_llm

# Create LLM using active provider from config
llm = create_llm()

# Create LLM for specific provider
llm = create_llm(provider_name="anthropic")

# Override parameters
llm = create_llm(model="gpt-4-turbo", temperature=0.5)
```

### Using Config Loader

```python
from llm_config import get_llm_config_loader

loader = get_llm_config_loader()
metadata = loader.get_metadata()

# Get active provider config
config = metadata.get_active_provider_config()

# Get specific provider config
config = metadata.get_provider_config("anthropic")

# List enabled providers
enabled = metadata.list_enabled_providers()
```

### Using Factory Directly

```python
from llm_config import get_llm_factory

factory = get_llm_factory()
llm = factory.create_llm(provider_name="google")
```

## Environment Variables

Set API keys in your `.env` file:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_API_KEY=...

# DeepSeek
DEEPSEEK_API_KEY=...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

## Configuration Features

### 1. Environment Variable Resolution

Configuration supports environment variable references:

```yaml
api_key: ${OPENAI_API_KEY}  # Resolved from environment
```

### 2. Default Values

Default settings apply to all providers:

```yaml
defaults:
  temperature: 0.3
  max_tokens: 2000
  timeout: 60
  max_retries: 3
```

### 3. Model-Specific Overrides

Override settings for specific models:

```yaml
model_overrides:
  gpt-4:
    temperature: 0.2
    max_tokens: 4000
  claude-3-opus-20240229:
    temperature: 0.3
    max_tokens: 4000
```

### 4. Provider Enable/Disable

Enable or disable providers:

```yaml
providers:
  openai:
    enabled: true  # Provider is active
  anthropic:
    enabled: false  # Provider is disabled
```

## Switching Providers

### Method 1: Change Active Provider

Edit `llm_config.yaml`:

```yaml
active_provider: anthropic  # Change from openai to anthropic
```

### Method 2: Use Specific Provider in Code

```python
llm = create_llm(provider_name="google")
```

### Method 3: Environment Variable

```bash
# Set active provider via environment (requires code support)
LLM_PROVIDER=anthropic
```

## Integration

The system is automatically integrated into:

- **DeepAgent** (`shared/deep_agent.py`) - Uses factory to create LLM
- **SCAP Agent** (`agents/scap_agent.py`) - Uses DeepAgent's LLM

No code changes needed - just update the YAML configuration.

## Error Handling

- **Missing API Key**: Returns `None`, logs warning
- **Provider Not Found**: Raises `ValueError`
- **Provider Disabled**: Raises `ValueError`
- **Package Not Installed**: Logs error, returns `None`

## Best Practices

1. **Keep API Keys in Environment**: Never commit API keys to YAML
2. **Use Defaults**: Define common settings in `defaults` section
3. **Model Overrides**: Use `model_overrides` for model-specific tuning
4. **Enable Only Needed Providers**: Disable unused providers
5. **Version Control**: Keep `llm_config.yaml` in version control (without API keys)

## Troubleshooting

### LLM is None

**Cause**: No API key or provider not configured

**Solution**: 
- Check API key is set in environment
- Verify provider is enabled in config
- Check provider name is correct

### Import Error

**Cause**: Required package not installed

**Solution**: Install required package:
```bash
pip install langchain-anthropic  # For Claude
pip install langchain-google-genai  # For Gemini
```

### Provider Not Found

**Cause**: Provider name doesn't match config

**Solution**: Check provider name in `llm_config.yaml` matches code

## Example Configurations

### Multi-Provider Setup

```yaml
active_provider: openai

providers:
  openai:
    enabled: true
    api_key: ${OPENAI_API_KEY}
    model: gpt-4
    
  anthropic:
    enabled: true
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-sonnet-20240229
    
  google:
    enabled: true
    api_key: ${GOOGLE_API_KEY}
    model: gemini-pro
```

### Development vs Production

Use different config files:

**Development** (`llm_config.dev.yaml`):
```yaml
active_provider: openai
providers:
  openai:
    model: gpt-3.5-turbo  # Cheaper model for dev
```

**Production** (`llm_config.prod.yaml`):
```yaml
active_provider: openai
providers:
  openai:
    model: gpt-4  # Better model for prod
```

Set via environment:
```bash
LLM_CONFIG_FILE=llm_config/llm_config.prod.yaml
```

