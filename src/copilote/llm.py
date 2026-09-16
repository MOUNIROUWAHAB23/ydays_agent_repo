"""Accès au LLM local et aux embeddings.

Les objets sont créés paresseusement (`lru_cache`) : importer le module ne
déclenche aucun appel réseau, ce qui rend les tests unitaires possibles sans
Ollama démarré.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_ollama import ChatOllama, OllamaEmbeddings

from .config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_llm(temperature: float = 0.0) -> ChatOllama:
    """Retourne un client Ollama.

    La température est un paramètre : le nœud de routage a besoin de 0.0
    (déterminisme), le rédacteur d'un peu de créativité.
    """
    logger.debug("Initialisation ChatOllama (model=%s, T=%.2f)", settings.llm_model, temperature)
    return ChatOllama(
        model=settings.llm_model,
        temperature=temperature,
        base_url=settings.ollama_base_url,
        timeout=settings.llm_timeout,
    )


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    logger.debug("Initialisation OllamaEmbeddings (model=%s)", settings.embedding_model)
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.ollama_base_url,
    )
