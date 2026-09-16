"""Outil métier : archivage de la candidature dans le Kanban Notion.

Point corrigé par rapport à la V1 : la lettre n'est plus tronquée à 2000
caractères. L'API Notion limite chaque objet `rich_text` à 2000 caractères ;
on découpe donc la lettre en plusieurs blocs paragraphe.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_core.tools import tool

from ..config import settings

logger = logging.getLogger(__name__)

# Marge de sécurité sous la limite Notion de 2000 caractères par rich_text.
NOTION_TEXT_LIMIT = 1900
STATUT_PAR_DEFAUT = "À postuler"


@lru_cache(maxsize=1)
def _client():
    from notion_client import Client

    return Client(auth=settings.notion_token)


def decouper_texte(texte: str, limite: int = NOTION_TEXT_LIMIT) -> list[str]:
    """Découpe un texte en morceaux <= `limite`, en respectant les paragraphes.

    Fonction pure : c'est elle qui est couverte par les tests unitaires.
    """
    if not texte:
        return []

    morceaux: list[str] = []
    courant = ""
    for paragraphe in texte.split("\n\n"):
        candidat = f"{courant}\n\n{paragraphe}" if courant else paragraphe
        if len(candidat) <= limite:
            courant = candidat
            continue
        if courant:
            morceaux.append(courant)
        # Un paragraphe seul peut dépasser la limite : on le coupe brutalement.
        while len(paragraphe) > limite:
            morceaux.append(paragraphe[:limite])
            paragraphe = paragraphe[limite:]
        courant = paragraphe
    if courant:
        morceaux.append(courant)
    return morceaux


def construire_blocs(lettre: str) -> list[dict]:
    """Construit les blocs Notion correspondant à la lettre de motivation."""
    blocs: list[dict] = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Lettre de motivation"}}]
            },
        }
    ]
    for morceau in decouper_texte(lettre):
        blocs.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": morceau}}]},
            }
        )
    return blocs


def construire_proprietes(entreprise: str, poste: str, lien_offre: str = "") -> dict:
    proprietes: dict = {
        "Nom": {"title": [{"text": {"content": entreprise[:200]}}]},
        "Statut": {"status": {"name": STATUT_PAR_DEFAUT}},
        "Poste": {"rich_text": [{"text": {"content": poste[:200]}}]},
    }
    if lien_offre:
        proprietes["Lien"] = {"url": lien_offre}
    return proprietes


@tool
def archiver_candidature(
    entreprise: str,
    poste: str,
    lettre_motivation: str,
    lien_offre: str = "",
) -> str:
    """Enregistre une candidature dans le Kanban Notion, lettre complète incluse.

    Args:
        entreprise: nom exact de l'entreprise.
        poste: intitulé exact du poste visé.
        lettre_motivation: texte INTÉGRAL de la lettre, pas un résumé.
        lien_offre: URL de l'offre si elle est connue.
    """
    if not settings.notion_enabled:
        logger.warning("Notion non configuré : archivage ignoré.")
        return "Archivage impossible : NOTION_TOKEN ou NOTION_DATABASE_ID manquant."

    if len(lettre_motivation.strip()) < 200:
        return (
            "Refus d'archiver : la lettre transmise est trop courte pour être "
            "une lettre complète. Rédige-la intégralement puis rappelle l'outil."
        )

    logger.info("Archivage Notion : %s — %s", entreprise, poste)
    try:
        _client().pages.create(
            parent={"database_id": settings.notion_database_id},
            properties=construire_proprietes(entreprise, poste, lien_offre),
            children=construire_blocs(lettre_motivation),
        )
    except Exception as exc:
        logger.exception("Échec de l'appel API Notion")
        return f"Échec de l'archivage Notion ({type(exc).__name__}: {exc})."

    return f"Candidature « {poste} » chez {entreprise} archivée dans Notion avec la lettre complète."
