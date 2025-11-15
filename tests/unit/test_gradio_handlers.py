"""Unit tests for Gradio helper utilities."""

import pytest

from app import check_environment


ENV_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "TAVILY_API_KEY",
    "EXA_API_KEY",
)


@pytest.fixture()
def reset_env(monkeypatch):
    """Clear relevant environment variables for each test."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_check_environment_missing_required(reset_env):
    """Ensure warning is shown when required secrets are absent."""
    html = check_environment()

    assert "OPENAI_API_KEY" in html
    assert "ANTHROPIC_API_KEY" in html
    assert "✗ Missing" in html
    assert "⚠ Warning" in html


def test_check_environment_all_configured(reset_env, monkeypatch):
    """Ensure configured secrets display success indicators."""
    for key in ENV_KEYS:
        monkeypatch.setenv(key, "configured")

    html = check_environment()

    assert "⚠ Warning" not in html
    for key in ENV_KEYS:
        assert f"{key}:</strong> ✓ Configured" in html
