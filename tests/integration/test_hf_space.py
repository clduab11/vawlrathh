"""Integration tests for Hugging Face Space wrapper.

Tests the HF Space wrapper including FastAPI startup, Gradio interface
creation, and async service integrations.
"""

import subprocess
import time

import httpx
import pytest
import pytest_asyncio


def test_app_imports():
    """Test that app.py imports without errors."""
    import app
    assert hasattr(app, 'main')
    assert hasattr(app, 'start_fastapi_server')
    assert hasattr(app, 'wait_for_fastapi_ready')
    assert hasattr(app, 'create_gradio_interface')
    # New async components
    assert hasattr(app, 'get_shared_client')
    assert hasattr(app, 'close_shared_client')


def test_gradio_interface_creation():
    """Test that Gradio interface can be created."""
    from app import create_gradio_interface
    
    interface = create_gradio_interface()
    assert interface is not None


def test_environment_check():
    """Test environment variable checking."""
    from app import check_environment
    
    html = check_environment()
    assert "Environment Configuration" in html
    assert "OPENAI_API_KEY" in html
    assert "ANTHROPIC_API_KEY" in html


def test_fastapi_server_can_start():
    """Test that FastAPI server can start and respond to health checks."""
    from app import start_fastapi_server, wait_for_fastapi_ready, kill_existing_uvicorn
    
    # Kill any existing servers
    kill_existing_uvicorn()
    time.sleep(2)
    
    # Start server
    process = start_fastapi_server()
    
    try:
        # Wait for it to be ready
        assert wait_for_fastapi_ready(max_wait=30), "FastAPI server did not become ready"
        
        # Test health endpoint
        response = httpx.get("http://localhost:7860/health", timeout=5.0)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
    finally:
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        kill_existing_uvicorn()


def test_kill_existing_uvicorn():
    """Test that kill_existing_uvicorn doesn't error."""
    from app import kill_existing_uvicorn

    # Should not raise an error even if no processes exist
    kill_existing_uvicorn()


@pytest.mark.asyncio
async def test_shared_client_lifecycle():
    """Test that shared client can be created and closed."""
    from app import get_shared_client, close_shared_client

    # Get client
    client = await get_shared_client()
    assert client is not None

    # Same client should be returned
    client2 = await get_shared_client()
    assert client is client2

    # Close client
    await close_shared_client()


@pytest.mark.asyncio
async def test_async_upload_handlers():
    """Test that async upload handlers work correctly with validation."""
    from app import _upload_csv_to_api, _upload_text_to_api

    # Test empty CSV
    result = await _upload_csv_to_api(None)
    assert result["status"] == "error"
    assert "No CSV" in result["message"]

    # Test empty text
    result = await _upload_text_to_api("", "Standard")
    assert result["status"] == "error"
    assert "empty" in result["message"].lower()


@pytest.mark.asyncio
async def test_async_meta_handlers():
    """Test that async meta handlers handle errors gracefully."""
    from app import _fetch_memory_summary

    # Test missing deck ID
    result = await _fetch_memory_summary(None)
    assert result["status"] == "error"
    assert "Deck ID required" in result["message"]
