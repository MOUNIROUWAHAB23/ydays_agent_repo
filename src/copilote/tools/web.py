"""Outil de veille : recherche d'actualités sur une entreprise (Tavily)."""

from __future__ import annotations

import logging

from langchain_core.tools import tool

from ..config import settings

logger = logging.getLogger(__name__)

MAX_SNIPPET = 800


def _format_results(payload: object) -> str:
    """Aplatit la réponse Tavily en texte lisible par le LLM.

    On ne renvoie jamais le JSON brut au modèle : un llama3.1 8B recopie
    volontiers des fragments de JSON dans sa réponse finale.
    """
    results = []
    if isinstance(payload, dict):
        results = payload.get("results", []) or []
    elif isinstance(payload, list):
        results = payload

    lignes: list[str] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        titre = str(item.get("title", "")).strip()
        contenu = str(item.get("content", "")).strip()[:MAX_SNIPPET]
        url = str(item.get("url", "")).strip()
        if contenu:
            lignes.append(f"- {titre or 'Sans titre'} ({url})\n  {contenu}")

    return "\n".join(lignes) if lignes else "Aucun résultat exploitable."


@tool
def recherche_entreprise(query: str) -> str:
    """Recherche les actualités récentes d'une entreprise sur le web.

    Args:
        query: nom de l'entreprise, éventuellement complété
               (ex. "Doctolib actualités recrutement data 2026").
    """
    if not settings.web_search_enabled:
        logger.warning("TAVILY_API_KEY absente : veille web désactivée.")
        return "Veille web indisponible (clé API non configurée)."

    logger.info("Veille web sur : %s", query)
    try:
        from langchain_tavily import TavilySearch

        search = TavilySearch(max_results=settings.tavily_max_results)
        return _format_results(search.invoke(query))
    except Exception as exc:  # réseau, quota, clé invalide…
        logger.exception("Échec de la recherche web")
        return (
            "La veille web a échoué "
            f"({type(exc).__name__}). Rédige sans information externe et "
            "signale-le à l'utilisateur."
        )
