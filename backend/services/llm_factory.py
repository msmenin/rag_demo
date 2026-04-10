"""LLM factory for creating provider instances from configuration."""
import os
import yaml
from pathlib import Path
from typing import Optional
from llama_index.core.llms import LLM

from backend.schemas.provider_config import ProviderConfig
from backend.services.providers.registry import get_provider_class


def create_llm(config_path: Path = Path("backend/config/providers.yaml")) -> LLM:
    """Create LLM instance from configuration file.
    
    Args:
        config_path: Path to providers.yaml configuration file
        
    Returns:
        Configured LlamaIndex LLM instance
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If required environment variables are not set
    """
    # Load configuration
    if not config_path.exists():
        raise FileNotFoundError(
            f"Provider configuration file not found: {config_path}"
        )
    
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    
    # Validate configuration
    config = ProviderConfig(**config_dict)
    
    # Get default LLM provider config
    llm_config = config.llm
    provider_name = llm_config["default"]
    provider_config = llm_config["providers"][provider_name]
    
    # Get API key from environment
    api_key_env = provider_config["api_key_env"]
    api_key = os.environ.get(api_key_env)
    
    if not api_key:
        raise ValueError(
            f"Missing required environment variable: {api_key_env}. "
            f"Set it in your .env file."
        )
    
    # Get provider class
    provider_class = get_provider_class(provider_config["type"])
    
    # Build provider kwargs
    kwargs = {
        "model": provider_config["model"],
        "api_key": api_key,
    }
    
    # Add optional base_url for OpenAI-compatible providers
    if provider_config.get("base_url"):
        kwargs["api_base"] = provider_config["base_url"]
    
    # Add optional extra_headers
    if provider_config.get("extra_headers"):
        kwargs["default_headers"] = provider_config["extra_headers"]
    
    # Create and return LLM instance
    return provider_class(**kwargs)


def validate_provider_config(
    config_path: Path = Path("backend/config/providers.yaml")
) -> None:
    """Validate provider configuration and environment variables.
    
    Args:
        config_path: Path to providers.yaml configuration file
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid or environment variables missing
    """
    # Check file exists
    if not config_path.exists():
        raise FileNotFoundError(
            f"Provider configuration file not found: {config_path}"
        )
    
    # Load and validate configuration
    with open(config_path) as f:
        config_dict = yaml.safe_load(f)
    
    config = ProviderConfig(**config_dict)
    
    # Check LLM provider API key
    llm_config = config.llm
    provider_name = llm_config["default"]
    provider_config = llm_config["providers"][provider_name]
    api_key_env = provider_config["api_key_env"]
    
    if not os.environ.get(api_key_env):
        raise ValueError(
            f"Missing required environment variable: {api_key_env}. "
            f"Set it in your .env file."
        )
    
    # Check embedding provider API key (if specified)
    embeddings_config = config.embeddings
    provider_name = embeddings_config["default"]
    provider_config = embeddings_config["providers"][provider_name]
    
    if provider_config.get("api_key_env"):
        api_key_env = provider_config["api_key_env"]
        if not os.environ.get(api_key_env):
            raise ValueError(
                f"Missing required environment variable: {api_key_env}. "
                f"Set it in your .env file."
            )
