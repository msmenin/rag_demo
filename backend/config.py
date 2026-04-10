from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag_app.db"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    PROVIDER_CONFIG_PATH: str = "backend/config/providers.yaml"
    
    # LLM Provider API Keys
    OPENROUTER_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # Capacity limits for workspace isolation and ChromaDB performance
    # Each workspace can have up to 50 PDF documents
    # This limit ensures reasonable query performance with embedded ChromaDB
    MAX_DOCUMENTS_PER_WORKSPACE: int = 50
    
    # ChromaDB configuration
    CHROMA_DB_PATH: str = "./chroma_db"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
