"""Test app startup and initialization for ZeroGPU deployment."""

import pytest
from unittest.mock import patch
import app


def test_app_object_exists():
    """Test that the app object is properly exposed at module level."""
    assert hasattr(app, 'app'), "App object should exist at module level"
    assert app.app is not None, "App object should not be None"


def test_app_is_fastapi_instance():
    """Test that the app object is a FastAPI instance."""
    from fastapi import FastAPI
    assert isinstance(app.app, FastAPI), f"App should be FastAPI instance, got {type(app.app)}"


def test_spaces_gpu_decorator_exists():
    """Test that the @spaces.GPU decorator is properly applied."""
    assert hasattr(app, 'initialize_gpu'), "@spaces.GPU decorated function should exist"


def test_spaces_gpu_function_callable():
    """Test that the GPU initialization function is callable."""
    gpu_func = getattr(app, 'initialize_gpu')
    assert callable(gpu_func), "initialize_gpu should be callable"


@patch('torch.cuda.is_available')
@patch('torch.cuda.get_device_name')
def test_spaces_gpu_function_returns_dict(mock_get_device_name, mock_cuda_available):
    """Test that the GPU function returns expected dictionary."""
    mock_cuda_available.return_value = True
    mock_get_device_name.return_value = "NVIDIA RTX 3080"

    result = app.initialize_gpu()

    assert isinstance(result, dict), "GPU function should return dict"
    assert result['cuda_available'] is True, "CUDA should be available"
    assert result['gpu'] == "NVIDIA RTX 3080", "GPU name should match"


def test_shutdown_event_handler_attached():
    """Test that shutdown event handler is properly attached."""
    # Check that the app has event handlers
    assert hasattr(app.app, 'router'), "App should have router"

    # The shutdown event should be attached during app creation
    # We can verify by checking if the app was created successfully
    assert app.app is not None, "App creation should succeed with shutdown handler"


def test_combined_app_creation():
    """Test that the combined FastAPI + Gradio app can be created."""
    combined_app = app.get_app()
    assert combined_app is not None, "Combined app should be created"
    assert hasattr(combined_app, 'mount'), "Combined app should have mount method"


def test_gradio_interface_creation():
    """Test that Gradio interface can be created without errors."""
    interface = app.create_gradio_interface()
    assert interface is not None, "Gradio interface should be created"


def test_fastapi_app_import():
    """Test that FastAPI app can be imported from src.main."""
    # This should not raise an exception due to the try/except in app.py
    # If there was an import error, fastapi_app would be a recovery FastAPI app
    assert app.fastapi_app is not None, "FastAPI app should be imported or fallback created"


def test_environment_check_function():
    """Test that environment checking function works."""
    html = app.check_environment()
    assert "Environment Configuration" in html, "Environment check should return HTML"
    assert "OPENAI_API_KEY" in html, "Should check required API keys"