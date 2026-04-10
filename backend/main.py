from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
import os
import yaml
from backend.config import settings
from backend.database import init_db
from backend.routers import workspace_router, documents_router
from backend.routers import query as query_router
from backend.services.llm_factory import validate_provider_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    # Validate provider configuration before initializing database
    validate_provider_config(config_path=Path(settings.PROVIDER_CONFIG_PATH))
    await init_db()
    yield
    # Shutdown (if needed)


# Create FastAPI application
app = FastAPI(
    title="RAG Document Assistant",
    description="A multi-tenant RAG application for document querying",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/health/providers")
async def health_providers():
    """Provider configuration health check endpoint.
    
    Returns provider status without exposing API keys.
    """
    config_path = Path(settings.PROVIDER_CONFIG_PATH)
    
    if not config_path.exists():
        return {
            "error": "Provider configuration file not found",
            "llm": None,
            "embeddings": None
        }
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Get LLM provider info
    llm_config = config.get("llm", {})
    llm_default = llm_config.get("default")
    llm_provider_config = llm_config.get("providers", {}).get(llm_default, {})
    
    llm_info = {
        "provider": llm_default,
        "model": llm_provider_config.get("model"),
        "api_key_configured": bool(os.environ.get(llm_provider_config.get("api_key_env", "")))
    }
    
    # Get embedding provider info
    embeddings_config = config.get("embeddings", {})
    embeddings_default = embeddings_config.get("default")
    embeddings_provider_config = embeddings_config.get("providers", {}).get(embeddings_default, {})
    
    embeddings_info = {
        "provider": embeddings_default,
        "model": embeddings_provider_config.get("model"),
        "api_key_configured": bool(os.environ.get(embeddings_provider_config.get("api_key_env", "")))
        if embeddings_provider_config.get("api_key_env") else True
    }
    
    return {
        "llm": llm_info,
        "embeddings": embeddings_info
    }


# Include routers
app.include_router(workspace_router)
app.include_router(documents_router)
app.include_router(query_router.router)
