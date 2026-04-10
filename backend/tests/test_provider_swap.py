"""Integration tests for provider swap functionality."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

from backend.services.llm_factory import create_llm
from backend.services.embedding_factory import create_embedding_model


class TestProviderSwap:
    """Tests for provider swapping via configuration."""

    def test_llm_provider_swap(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Swapping LLM provider in config changes returned LLM instance."""
        # Arrange - create two configs with different providers
        config1_content = """
llm:
  default: openrouter
  providers:
    openrouter:
      type: openai_compatible
      model: anthropic/claude-3.5-sonnet
      api_key_env: TEST_API_KEY
      base_url: https://openrouter.ai/api/v1
      extra_headers:
        HTTP-Referer: http://localhost:3000
        X-Title: Test App

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config2_content = """
llm:
  default: openai_direct
  providers:
    openai_direct:
      type: openai
      model: gpt-4o-mini
      api_key_env: TEST_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config1_path = tmp_path / "providers1.yaml"
        config2_path = tmp_path / "providers2.yaml"
        config1_path.write_text(config1_content)
        config2_path.write_text(config2_content)
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        
        # Act - create LLMs from different configs
        llm1 = create_llm(config1_path)
        llm2 = create_llm(config2_path)
        
        # Assert - both are OpenAI instances (OpenAI-compatible)
        assert isinstance(llm1, OpenAI)
        assert isinstance(llm2, OpenAI)
        # Different model names
        assert llm1.model == "anthropic/claude-3.5-sonnet"
        assert llm2.model == "gpt-4o-mini"

    def test_embedding_provider_swap(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Swapping embedding provider in config changes returned embedding instance."""
        # Arrange - create two configs with different embedding models
        config1_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: TEST_API_KEY

embeddings:
  default: openai_small
  providers:
    openai_small:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config2_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: TEST_API_KEY

embeddings:
  default: openai_large
  providers:
    openai_large:
      type: openai
      model: text-embedding-3-large
      api_key_env: TEST_API_KEY
"""
        config1_path = tmp_path / "providers1.yaml"
        config2_path = tmp_path / "providers2.yaml"
        config1_path.write_text(config1_content)
        config2_path.write_text(config2_content)
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        
        # Act - create embeddings from different configs
        embed1 = create_embedding_model(config1_path)
        embed2 = create_embedding_model(config2_path)
        
        # Assert - both are OpenAIEmbedding instances
        assert isinstance(embed1, OpenAIEmbedding)
        assert isinstance(embed2, OpenAIEmbedding)
        # Different model names
        assert embed1.model_name == "text-embedding-3-small"
        assert embed2.model_name == "text-embedding-3-large"

    def test_both_factories_same_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Both factories can use same config file."""
        # Arrange
        config_content = """
llm:
  default: openrouter
  providers:
    openrouter:
      type: openai_compatible
      model: anthropic/claude-3.5-sonnet
      api_key_env: TEST_API_KEY
      base_url: https://openrouter.ai/api/v1

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        
        # Act - create both from same config
        llm = create_llm(config_path)
        embed = create_embedding_model(config_path)
        
        # Assert - both created successfully
        assert isinstance(llm, OpenAI)
        assert isinstance(embed, OpenAIEmbedding)

    def test_invalid_provider_type(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Invalid provider type raises clear error."""
        # Arrange
        config_content = """
llm:
  default: unknown_provider
  providers:
    unknown_provider:
      type: unknown_type
      model: some-model
      api_key_env: TEST_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            create_llm(config_path)
        
        assert "unknown_type" in str(exc_info.value).lower()

    def test_config_reload(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Factory picks up config changes on next call."""
        # Arrange - start with one config
        config_content1 = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: TEST_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content1)
        monkeypatch.setenv("TEST_API_KEY", "sk-test-key")
        
        # Act - create first LLM
        llm1 = create_llm(config_path)
        assert llm1.model == "gpt-4o-mini"
        
        # Modify config
        config_content2 = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o
      api_key_env: TEST_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: TEST_API_KEY
"""
        config_path.write_text(config_content2)
        
        # Act - create second LLM
        llm2 = create_llm(config_path)
        
        # Assert - different model loaded
        assert llm2.model == "gpt-4o"
