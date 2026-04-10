"""Provider configuration schema for LLM and embedding providers."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator


class LLMProviderConfig(BaseModel):
    """Configuration for an LLM provider."""
    
    type: str
    model: str
    api_key_env: str
    base_url: Optional[str] = None
    extra_headers: Optional[Dict[str, str]] = None


class EmbeddingProviderConfig(BaseModel):
    """Configuration for an embedding provider."""
    
    type: str
    model: str
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None


class ProviderConfig(BaseModel):
    """Overall provider configuration for LLM and embedding providers."""
    
    llm: Dict[str, Any]
    embeddings: Dict[str, Any]
    
    @field_validator('llm')
    @classmethod
    def validate_llm_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that default LLM provider exists in providers dict."""
        if 'default' not in v:
            raise ValueError('llm config must have a "default" field')
        if 'providers' not in v:
            raise ValueError('llm config must have a "providers" field')
        
        default = v['default']
        providers = v['providers']
        
        if default not in providers:
            raise ValueError(
                f'Default LLM provider "{default}" not found in providers'
            )
        
        # Validate each provider config
        for provider_name, provider_config in providers.items():
            LLMProviderConfig(**provider_config)
        
        return v
    
    @field_validator('embeddings')
    @classmethod
    def validate_embeddings_config(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that default embedding provider exists in providers dict."""
        if 'default' not in v:
            raise ValueError('embeddings config must have a "default" field')
        if 'providers' not in v:
            raise ValueError('embeddings config must have a "providers" field')
        
        default = v['default']
        providers = v['providers']
        
        if default not in providers:
            raise ValueError(
                f'Default embedding provider "{default}" not found in providers'
            )
        
        # Validate each provider config
        for provider_name, provider_config in providers.items():
            EmbeddingProviderConfig(**provider_config)
        
        return v
