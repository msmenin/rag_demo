"""Embedding factory for creating embedding model instances from configuration."""
import os
import yaml
from pathlib import Path
from typing import Optional
from llama_index.core.embeddings import BaseEmbedding

from backend.schemas.provider_config import ProviderConfig
from backend.services.providers.registry import get_embedding_class


def create_embedding_model(
    config_path: Path = Path("backend/config/providers.yaml")
) -> BaseEmbedding:
    """Create embedding model instance from configuration file.
    
    Args:
        config_path: Path to providers.yaml configuration file
        
    Returns:
        Configured LlamaIndex BaseEmbedding instance
        
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
    
    # Get default embedding provider config
    embeddings_config = config.embeddings
    provider_name = embeddings_config["default"]
    provider_config = embeddings_config["providers"][provider_name]
    
    # Get API key from environment (optional for some providers like HuggingFace)
    api_key_env = provider_config.get("api_key_env")
    api_key: Optional[str] = None
    
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(
                f"Missing required environment variable: {api_key_env}. "
                f"Set it in your .env file."
            )
    
    # Get provider class
    provider_class = get_embedding_class(provider_config["type"])
    
    # Build provider kwargs
    kwargs: dict = {
        "model_name": provider_config["model"],
    }
    
    # Add API key if provided
    if api_key:
        kwargs["api_key"] = api_key
    
    # Add optional base_url for custom endpoints
    if provider_config.get("base_url"):
        kwargs["api_base"] = provider_config["base_url"]
    
    # Create and return embedding model instance
    return provider_class(**kwargs)
