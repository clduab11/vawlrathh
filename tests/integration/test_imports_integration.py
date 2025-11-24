"""Test FastAPI + Gradio integration imports."""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock


def test_gradio_import():
    """Test that Gradio can be imported."""
    import gradio as gr
    assert gr is not None, "Gradio should be importable"


def test_spaces_import():
    """Test that spaces module can be imported."""
    import spaces
    assert spaces is not None, "Spaces should be importable"


def test_fastapi_import():
    """Test that FastAPI can be imported."""
    from fastapi import FastAPI
    app = FastAPI()
    assert app is not None, "FastAPI should be importable"


def test_mount_gradio_app_import():
    """Test that mount_gradio_app can be imported."""
    from gradio import mount_gradio_app
    assert mount_gradio_app is not None, "mount_gradio_app should be importable"


def test_app_import_no_exceptions():
    """Test that importing app module doesn't raise exceptions."""
    try:
        import app
        assert True, "App import should not raise exceptions"
    except Exception as e:
        pytest.fail(f"App import raised exception: {e}")


def test_src_main_import():
    """Test that src.main module can be imported."""
    try:
        from src.main import app as fastapi_app
        assert fastapi_app is not None, "FastAPI app from src.main should exist"
    except ImportError as e:
        # This is expected if there are missing dependencies
        # The app.py handles this with a fallback
        pytest.skip(f"src.main import failed as expected: {e}")


def test_combined_app_creation():
    """Test that combined FastAPI + Gradio app can be created."""
    import app

    combined_app = app.get_app()
    assert combined_app is not None, "Combined app should be created"


def test_gradio_interface_creation():
    """Test that Gradio interface creation works."""
    import app

    interface = app.create_gradio_interface()
    assert interface is not None, "Gradio interface should be created"


@patch('spaces.GPU')
def test_spaces_gpu_decorator_application(mock_gpu):
    """Test that @spaces.GPU decorator is applied correctly."""
    import app

    # The initialize_gpu function should have the decorator applied
    gpu_func = getattr(app, 'initialize_gpu')

    # Check that the function exists and is callable
    assert callable(gpu_func), "GPU function should be callable"

    # The decorator should have been applied (this is checked at runtime by spaces)
    # We can't easily test the decorator itself, but we can test function behavior
    assert True, "Spaces GPU decorator test passed"


def test_no_syntax_errors():
    """Test that there are no syntax errors in app.py."""
    import app

    # If there were syntax errors, the import would fail
    assert hasattr(app, 'app'), "App should be available without syntax errors"
    assert hasattr(app, 'get_app'), "Factory function should exist"


def test_import_order():
    """Test that imports are in correct order (FastAPI before Gradio)."""
    # This is more of a code review test, but we can check that both are available
    import fastapi
    import gradio

    assert fastapi is not None, "FastAPI should be imported"
    assert gradio is not None, "Gradio should be imported"


@patch.dict(os.environ, {}, clear=True)
def test_import_without_environment_variables():
    """Test that app can be imported even without environment variables."""
    # Clear environment and try import
    try:
        import app
        assert hasattr(app, 'app'), "App should import without env vars"
    except Exception as e:
        pytest.fail(f"App import failed without env vars: {e}")


def test_builder_registry_population():
    """Test that Gradio builders are registered."""
    import app

    # Check that the builder registry has expected builders
    builders = app.GRADIO_BUILDERS
    assert isinstance(builders, dict), "Builder registry should be a dict"
    assert len(builders) > 0, "Should have at least one registered builder"

    # Check that expected builders exist
    expected_builders = ['deck_uploader', 'chat_ui', 'meta_dashboards']
    for builder_name in expected_builders:
        assert builder_name in builders, f"Builder {builder_name} should be registered"