"""Assemblage du graphe d'état.

           ┌──────────┐
           │  profil  │  (RAG ChromaDB)
           └────┬─────┘
                ▼
        ┌───────────────┐
        │ planificateur │  (classification + extraction JSON)
        └───┬───┬───┬───┘
   hors_sujet│   │   │candidature
        ┌────▼─┐ │ ┌─▼────────┐
        │garde │ │ │ veilleur │  (outil : recherche web)
        │ fou  │ │ └────┬─────┘
        └──┬───┘ │      ▼
           │  conseil ┌───────────┐
           │     │    │ redacteur │
           │  ┌──▼────▼──┐   │
           │  │conseiller│◄─┐│      ┌────────────┐
           │  └────┬─────┘  ││  ┌──►│ archiviste │  (outil : API Notion)
           │       ▼        ││  │   └─────┬──────┘
           │   ┌────────┐   ││  │         │
           │   │ outils ├───┘│  │         │
           │   └────────┘    │  │         │
           └────────────────►END◄─────────┘

Deux chemins cycliques (`conseiller ⇄ outils`) et un chemin séquentiel
conditionnel (`veilleur → redacteur → archiviste?`) : le graphe n'est pas
linéaire et chaque branche est bornée.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from . import nodes
from .state import AgentState


def construire_graphe():
    workflow = StateGraph(AgentState)

    workflow.add_node("chargement_profil", nodes.noeud_profil)
    workflow.add_node("planificateur", nodes.noeud_planificateur)
    workflow.add_node("garde_fou", nodes.noeud_garde_fou)
    workflow.add_node("conseiller", nodes.noeud_conseiller)
    workflow.add_node("outils", nodes.noeud_outils)
    workflow.add_node("veilleur", nodes.noeud_veilleur)
    workflow.add_node("redacteur", nodes.noeud_redacteur)
    workflow.add_node("verificateur", nodes.noeud_verificateur)
    workflow.add_node("archiviste", nodes.noeud_archiviste)

    workflow.set_entry_point("chargement_profil")
    workflow.add_edge("chargement_profil", "planificateur")

    workflow.add_conditional_edges(
        "planificateur",
        nodes.routeur_intention,
        {"veilleur": "veilleur", "conseiller": "conseiller", "garde_fou": "garde_fou"},
    )

    # Branche conseil : boucle ReAct bornée
    workflow.add_conditional_edges(
        "conseiller",
        nodes.routeur_outils,
        {"outils": "outils", "fin": END},
    )
    workflow.add_edge("outils", "conseiller")

    # Branche candidature : rédaction -> contrôle factuel -> archivage
    workflow.add_edge("veilleur", "redacteur")
    workflow.add_edge("redacteur", "verificateur")
    workflow.add_conditional_edges(
        "verificateur",
        nodes.routeur_verification,
        {"verificateur": "verificateur", "suite": "sauvegarde", "fin": END},
    )
    # Nœud de passage : permet de router vers l'archivage sans dupliquer la
    # condition de sauvegarde dans le vérificateur.
    workflow.add_node("sauvegarde", lambda state: {})
    workflow.add_conditional_edges(
        "sauvegarde",
        nodes.routeur_sauvegarde,
        {"archiviste": "archiviste", "fin": END},
    )
    workflow.add_edge("archiviste", END)

    workflow.add_edge("garde_fou", END)

    return workflow.compile()


_app = None


def get_app():
    """Compilation paresseuse : importer le module ne construit rien."""
    global _app
    if _app is None:
        _app = construire_graphe()
    return _app
