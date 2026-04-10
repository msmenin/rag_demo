"""Provider registry mapping provider types to LlamaIndex classes."""
from typing import Type
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import LLM
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings import BaseEmbedding


# Registry mapping provider type strings to LlamaIndex LLM classes
PROVIDER_REGISTRY: dict[str, Type[LLM]] = {
    "openai": OpenAI,
    "openai_compatible": OpenAI,  # Same class, different configuration
}


# Registry mapping provider type strings to LlamaIndex Embedding classes
EMBEDDING_REGISTRY: dict[str, Type[BaseEmbedding]] = {
    "openai": OpenAIEmbedding,
    "huggingface": None,  # Placeholder for HuggingFace support in future
}


def get_provider_class(provider_type: str) -> Type[LLM]:
    """Get LlamaIndex LLM class for a provider type.
    
    Args:
        provider_type: Provider type string (e.g., "openai", "openai_compatible")
        
    Returns:
        LlamaIndex LLM class
        
    Raises:
        ValueError: If provider type not in registry
    """
    if provider_type not in PROVIDER_REGISTRY:
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Available types: {list(PROVIDER_REGISTRY.keys())}"
        )
    return PROVIDER_REGISTRY[provider_type]


def get_embedding_class(provider_type: str) -> Type[BaseEmbedding]:
    """Get LlamaIndex Embedding class for a provider type.
    
    Args:
        provider_type: Provider type string (e.g., "openai", "huggingface")
        
    Returns:
        LlamaIndex Embedding class
        
    Raises:
        ValueError: If provider type not in registry or not implemented
    """
    if provider_type not in EMBEDDING_REGISTRY:
        raise ValueError(
            f"Unknown embedding provider type: {provider_type}. "
            f"Available types: {list(EMBEDDING_REGISTRY.keys())}"
        )
    
    provider_class = EMBEDDING_REGISTRY[provider_type]
    if provider_class is None:
        raise ValueError(
            f"Embedding provider type '{provider_type}' is registered but not yet implemented. "
            f"Currently supported: {[k for k, v in EMBEDDING_REGISTRY.items() if v is not None]}"
        )
    
    return provider_class
