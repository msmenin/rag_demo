"""Tests for provider configuration schema."""
import pytest
from pathlib import Path
from pydantic import ValidationError
from backend.schemas.provider_config import (
    LLMProviderConfig,
    EmbeddingProviderConfig,
    ProviderConfig,
)


def test_llm_provider_config_validates_required_fields():
    """Test LLMProviderConfig validates required fields."""
    config = LLMProviderConfig(
        type="openai_compatible",
        model="anthropic/claude-3.5-sonnet",
        api_key_env="OPENROUTER_API_KEY",
    )
    assert config.type == "openai_compatible"
    assert config.model == "anthropic/claude-3.5-sonnet"
    assert config.api_key_env == "OPENROUTER_API_KEY"


def test_llm_provider_config_optional_fields():
    """Test LLMProviderConfig handles optional fields."""
    config = LLMProviderConfig(
        type="openai_compatible",
        model="anthropic/claude-3.5-sonnet",
        api_key_env="OPENROUTER_API_KEY",
        base_url="https://openrouter.ai/api/v1",
        extra_headers={"HTTP-Referer": "http://localhost:3000"},
    )
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.extra_headers == {"HTTP-Referer": "http://localhost:3000"}


def test_llm_provider_config_missing_required_field():
    """Test LLMProviderConfig raises error for missing required field."""
    with pytest.raises(ValidationError) as exc_info:
        LLMProviderConfig(
            type="openai_compatible",
            model="anthropic/claude-3.5-sonnet",
            # Missing api_key_env
        )
    assert "api_key_env" in str(exc_info.value)


def test_embedding_provider_config_validates_required_fields():
    """Test EmbeddingProviderConfig validates required fields."""
    config = EmbeddingProviderConfig(
        type="openai",
        model="text-embedding-3-small",
    )
    assert config.type == "openai"
    assert config.model == "text-embedding-3-small"


def test_embedding_provider_config_with_api_key_env():
    """Test EmbeddingProviderConfig with optional api_key_env."""
    config = EmbeddingProviderConfig(
        type="openai",
        model="text-embedding-3-small",
        api_key_env="OPENAI_API_KEY",
    )
    assert config.api_key_env == "OPENAI_API_KEY"


def test_provider_config_validates_structure():
    """Test ProviderConfig validates overall structure."""
    config_dict = {
        "llm": {
            "default": "openrouter",
            "providers": {
                "openrouter": {
                    "type": "openai_compatible",
                    "model": "anthropic/claude-3.5-sonnet",
                    "api_key_env": "OPENROUTER_API_KEY",
                    "base_url": "https://openrouter.ai/api/v1",
                }
            },
        },
        "embeddings": {
            "default": "openai",
            "providers": {
                "openai": {
                    "type": "openai",
                    "model": "text-embedding-3-small",
                    "api_key_env": "OPENAI_API_KEY",
                }
            },
        },
    }
    config = ProviderConfig(**config_dict)
    assert config.llm["default"] == "openrouter"
    assert "openrouter" in config.llm["providers"]
    assert config.embeddings["default"] == "openai"


def test_provider_config_validates_default_provider_exists():
    """Test ProviderConfig raises error if default provider not in providers."""
    config_dict = {
        "llm": {
            "default": "nonexistent",
            "providers": {
                "openrouter": {
                    "type": "openai_compatible",
                    "model": "anthropic/claude-3.5-sonnet",
                    "api_key_env": "OPENROUTER_API_KEY",
                }
            },
        },
        "embeddings": {
            "default": "openai",
            "providers": {
                "openai": {
                    "type": "openai",
                    "model": "text-embedding-3-small",
                }
            },
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        ProviderConfig(**config_dict)
    assert "nonexistent" in str(exc_info.value)


def test_example_yaml_loads_and_validates():
    """Test that example YAML config loads and validates successfully."""
    import yaml

    config_path = Path("backend/config/providers.example.yaml")
    if not config_path.exists():
        pytest.skip("Example config not yet created")

    with open(config_path) as f:
        config_dict = yaml.safe_load(f)

    # Should not raise validation error
    config = ProviderConfig(**config_dict)
    assert config.llm["default"] is not None
    assert config.embeddings["default"] is not None
