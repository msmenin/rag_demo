"""Provider registry mapping provider types to LlamaIndex classes."""
from typing import Type, Any
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import LLM


# Registry mapping provider type strings to LlamaIndex LLM classes
PROVIDER_REGISTRY: dict[str, Type[LLM]] = {
    "openai": OpenAI,
    "openai_compatible": OpenAI,  # Same class, different configuration
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
