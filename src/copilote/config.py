"""Configuration centralisée de l'application.

Toute la configuration passe par des variables d'environnement, validées au
démarrage. Aucune clé n'est écrite en dur dans le code.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]


class ConfigError(RuntimeError):
    """Configuration invalide ou incomplète."""


def _env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ConfigError(
            f"Variable d'environnement manquante : {name}. "
            "Copie .env.example vers .env et renseigne tes clés."
        )
    return value or ""


@dataclass(frozen=True)
class Settings:
    # --- LLM local (Ollama) ---
    ollama_base_url: str = field(
        default_factory=lambda: _env("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    )
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "llama3.1"))
    embedding_model: str = field(
        default_factory=lambda: _env("EMBEDDING_MODEL", "nomic-embed-text")
    )
    llm_timeout: int = field(default_factory=lambda: int(_env("LLM_TIMEOUT", "180")))

    # --- RAG ---
    chroma_dir: Path = field(
        default_factory=lambda: Path(_env("CHROMA_DIR", str(BASE_DIR / "chroma_db")))
    )
    documents_dir: Path = field(
        default_factory=lambda: Path(_env("DOCUMENTS_DIR", str(BASE_DIR / "data")))
    )
    collection_name: str = field(default_factory=lambda: _env("COLLECTION_NAME", "profil"))
    chunk_size: int = field(default_factory=lambda: int(_env("CHUNK_SIZE", "800")))
    chunk_overlap: int = field(default_factory=lambda: int(_env("CHUNK_OVERLAP", "120")))
    retrieval_k: int = field(default_factory=lambda: int(_env("RETRIEVAL_K", "6")))

    # --- Outils externes ---
    tavily_api_key: str = field(default_factory=lambda: _env("TAVILY_API_KEY"))
    tavily_max_results: int = field(default_factory=lambda: int(_env("TAVILY_MAX_RESULTS", "3")))
    notion_token: str = field(default_factory=lambda: _env("NOTION_TOKEN"))
    notion_database_id: str = field(default_factory=lambda: _env("NOTION_DATABASE_ID"))

    # --- Identité du candidat ---
    # Le CV peut contenir plusieurs graphies du nom (en-tête, URL LinkedIn) :
    # on fixe ici la forme officielle pour la signature des lettres.
    candidat_nom: str = field(default_factory=lambda: _env("CANDIDAT_NOM", ""))

    # --- Garde-fous du graphe ---
    max_iterations: int = field(default_factory=lambda: int(_env("MAX_ITERATIONS", "8")))
    max_corrections: int = field(default_factory=lambda: int(_env("MAX_CORRECTIONS", "2")))

    # --- Divers ---
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))

    @property
    def web_search_enabled(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def notion_enabled(self) -> bool:
        return bool(self.notion_token and self.notion_database_id)


settings = Settings()


def configure_logging() -> None:
    """Logging structuré : remplace les `print` dispersés dans le code."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
        datefmt="%H:%M:%S",
        force=True,   # Streamlit installe ses propres handlers : on les remplace
    )
    # Les libs tierces sont bavardes en DEBUG
    for noisy in ("httpx", "httpcore", "chromadb", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
