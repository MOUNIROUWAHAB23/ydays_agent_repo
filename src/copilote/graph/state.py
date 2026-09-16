"""État partagé entre les nœuds du graphe."""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

Intention = Literal["candidature", "conseil", "hors_sujet"]


class AgentState(TypedDict, total=False):
    """Mémoire de travail du graphe.

    `messages` utilise le réducteur `add_messages` de LangGraph (et non
    `operator.add`) : il déduplique par identifiant et gère correctement
    l'appariement AIMessage / ToolMessage, ce qui évite les historiques
    corrompus après un appel d'outil.
    """

    messages: Annotated[list[BaseMessage], add_messages]

    # Contexte issu du RAG sur les documents du candidat
    profil: str

    # Plan produit par le nœud planificateur
    intention: Intention
    entreprise: str
    poste: str
    lien_offre: str
    sauvegarder: bool

    # Texte brut de l'offre fourni par le candidat
    offre: str

    # Résultats intermédiaires
    veille: str
    lettre: str

    # Contrôle factuel de la lettre
    violations: list[str]
    corrections: int
    lettre_conforme: bool

    # Garde-fou anti-boucle infinie
    iterations: int
