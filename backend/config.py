from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag_app.db"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    PROVIDER_CONFIG_PATH: str = "backend/config/providers.yaml"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
