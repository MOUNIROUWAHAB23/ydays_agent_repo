"""Outils exposés à l'agent (tool calling)."""

from .notion import archiver_candidature
from .web import recherche_entreprise

TOOLS = [recherche_entreprise, archiver_candidature]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}

__all__ = ["TOOLS", "TOOLS_BY_NAME", "recherche_entreprise", "archiver_candidature"]
