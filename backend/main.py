from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from backend.config import settings
from backend.database import init_db
from backend.routers import workspace_router, documents_router
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


# Include routers
app.include_router(workspace_router)
app.include_router(documents_router)
