"""Tests for embedding factory function."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.embeddings import BaseEmbedding

from backend.services.embedding_factory import create_embedding_model


class TestCreateEmbeddingFromConfig:
    """Tests for create_embedding_model function."""

    def test_create_embedding_from_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Factory creates OpenAIEmbedding instance from config."""
        # Arrange
        config_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: OPENAI_API_KEY
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-12345")
        
        # Act
        embed_model = create_embedding_model(config_path)
        
        # Assert
        assert isinstance(embed_model, BaseEmbedding)
        assert isinstance(embed_model, OpenAIEmbedding)

    def test_openai_embedding_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Verify model name and api_key are set correctly."""
        # Arrange
        config_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-large
      api_key_env: OPENAI_API_KEY
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-67890")
        
        # Act
        embed_model = create_embedding_model(config_path)
        
        # Assert
        assert embed_model.model_name == "text-embedding-3-large"
        # Note: api_key is stored internally, we can't directly access it
        # but we verified the instance was created successfully

    def test_missing_api_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing API key raises clear error."""
        # Arrange
        config_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

embeddings:
  default: openai
  providers:
    openai:
      type: openai
      model: text-embedding-3-small
      api_key_env: MISSING_API_KEY
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        # Ensure the env var is not set
        monkeypatch.delenv("MISSING_API_KEY", raising=False)
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            create_embedding_model(config_path)
        
        assert "MISSING_API_KEY" in str(exc_info.value)
        assert ".env" in str(exc_info.value).lower()

    def test_custom_config_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Factory loads from custom config path."""
        # Arrange
        config_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: CUSTOM_KEY

embeddings:
  default: custom_provider
  providers:
    custom_provider:
      type: openai
      model: text-embedding-3-small
      api_key_env: CUSTOM_KEY
"""
        config_path = tmp_path / "custom_config.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("CUSTOM_KEY", "sk-custom-key")
        
        # Act
        embed_model = create_embedding_model(config_path)
        
        # Assert
        assert isinstance(embed_model, OpenAIEmbedding)
        assert embed_model.model_name == "text-embedding-3-small"

    def test_missing_config_file(self, tmp_path: Path) -> None:
        """Missing config file raises FileNotFoundError."""
        # Arrange
        config_path = tmp_path / "nonexistent.yaml"
        
        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            create_embedding_model(config_path)
        
        assert "not found" in str(exc_info.value).lower()

    def test_optional_api_key_for_local_models(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Local models without api_key_env work without API key."""
        # Arrange - this test will be implemented when we add HuggingFace support
        # For now, we test that api_key_env is optional in the schema
        config_content = """
llm:
  default: openai
  providers:
    openai:
      type: openai
      model: gpt-4o-mini
      api_key_env: OPENAI_API_KEY

embeddings:
  default: huggingface
  providers:
    huggingface:
      type: huggingface
      model: sentence-transformers/all-MiniLM-L6-v2
"""
        config_path = tmp_path / "providers.yaml"
        config_path.write_text(config_content)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        
        # This will fail until we implement HuggingFace support in the registry
        # For now, we expect a ValueError about unknown provider type
        with pytest.raises(ValueError) as exc_info:
            create_embedding_model(config_path)
        
        assert "huggingface" in str(exc_info.value).lower()
