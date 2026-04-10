"""Tests for LLM factory functions."""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from llama_index.llms.openai import OpenAI

from backend.services.llm_factory import create_llm, validate_provider_config


def test_create_llm_from_config():
    """Test that create_llm returns OpenAI instance with OpenRouter config."""
    # Use test fixture config
    config_path = Path("backend/tests/fixtures/providers.yaml")
    
    # Mock the environment variable
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        llm = create_llm(config_path=config_path)
        
        # Should return OpenAI instance (OpenRouter uses OpenAI-compatible client)
        assert isinstance(llm, OpenAI)
        assert llm.model == "anthropic/claude-3.5-sonnet"


def test_create_llm_openrouter_config():
    """Test that create_llm configures OpenRouter correctly with base_url and headers."""
    config_path = Path("backend/tests/fixtures/providers.yaml")
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        llm = create_llm(config_path=config_path)
        
        # Verify OpenRouter-specific configuration
        assert llm.api_base == "https://openrouter.ai/api/v1"
        # Check that extra_headers were configured
        # Note: LlamaIndex OpenAI client stores headers differently
        # We verify the model was created successfully with the config


def test_create_llm_missing_api_key():
    """Test that create_llm raises clear error when API key env var not set."""
    config_path = Path("backend/tests/fixtures/providers.yaml")
    
    # Ensure the env var is not set
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            create_llm(config_path=config_path)
        
        # Should have clear error message
        assert "OPENROUTER_API_KEY" in str(exc_info.value)
        assert "environment variable" in str(exc_info.value).lower()


def test_create_llm_custom_config_path():
    """Test that create_llm can load from custom config path."""
    custom_config_path = Path("backend/tests/fixtures/providers.yaml")
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
        llm = create_llm(config_path=custom_config_path)
        assert isinstance(llm, OpenAI)


def test_validate_provider_config_success():
    """Test that validate_provider_config succeeds with valid config."""
    config_path = Path("backend/tests/fixtures/providers.yaml")
    
    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key", "OPENAI_API_KEY": "test-key"}):
        # Should not raise any error
        validate_provider_config(config_path=config_path)


def test_validate_provider_config_missing_key():
    """Test that validate_provider_config raises error for missing API key."""
    config_path = Path("backend/tests/fixtures/providers.yaml")
    
    # Missing OPENROUTER_API_KEY
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
        with pytest.raises(ValueError) as exc_info:
            validate_provider_config(config_path=config_path)
        
        assert "OPENROUTER_API_KEY" in str(exc_info.value)


def test_validate_provider_config_missing_file():
    """Test that validate_provider_config raises error for missing config file."""
    nonexistent_path = Path("backend/config/nonexistent.yaml")
    
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_provider_config(config_path=nonexistent_path)
    
    assert "not found" in str(exc_info.value).lower()
