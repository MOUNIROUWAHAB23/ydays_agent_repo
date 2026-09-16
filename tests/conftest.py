"""Fixtures communes : aucun test ne doit toucher au réseau ni à Ollama."""

import os

import pytest

os.environ.setdefault("TAVILY_API_KEY", "test-key")
os.environ.setdefault("NOTION_TOKEN", "test-token")
os.environ.setdefault("NOTION_DATABASE_ID", "test-db")
os.environ.setdefault("LOG_LEVEL", "CRITICAL")


@pytest.fixture
def lettre_longue() -> str:
    paragraphe = "Ceci est un paragraphe de lettre de motivation. " * 30
    return "\n\n".join([paragraphe] * 4)
