import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
from pathlib import Path
from backend.main import app
from backend.database import Base, get_db

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_rag_app.db"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine):
    """Create a test database session."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def async_client(db_session):
    """Create an async test client."""
    from backend.models import Workspace

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def workspace(async_client):
    """Create a test workspace for upload tests."""
    from backend.models import Workspace

    response = await async_client.post("/workspace/")
    assert response.status_code == 200

    return Workspace(**response.json())


@pytest.fixture
def test_pdf_small():
    """Small PDF (1-2 pages) for quick tests."""
    pdf_path = Path(__file__).parent / "fixtures" / "test_small.pdf"
    if not pdf_path.exists():
        # Create a simple PDF for testing
        import fitz  # PyMuPDF

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Test document for RAG pipeline. " * 50)
        page.insert_text((100, 200), "This is page 1 content for semantic chunking tests.")
        doc.save(str(pdf_path))
        doc.close()

    with open(pdf_path, "rb") as f:
        return f.read()


@pytest.fixture
def test_pdf_medium():
    """Medium PDF (~10 pages) for performance tests."""
    pdf_path = Path(__file__).parent / "fixtures" / "test_medium.pdf"
    if not pdf_path.exists():
        import fitz

        doc = fitz.open()
        for i in range(10):
            page = doc.new_page()
            page.insert_text((100, 100), f"Page {i+1} of test document. " * 100)
            page.insert_text((100, 200), f"This is content for page {i+1} with more text for chunking.")
        doc.save(str(pdf_path))
        doc.close()

    with open(pdf_path, "rb") as f:
        return f.read()


@pytest.fixture
def test_pdf_invalid():
    """Invalid PDF for error handling tests."""
    return b"This is not a valid PDF file content"
