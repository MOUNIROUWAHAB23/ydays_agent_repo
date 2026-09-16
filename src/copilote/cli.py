"""Interface en ligne de commande.

Les étapes affichées proviennent du **vrai** flux d'exécution du graphe
(`app.stream`), et non d'un scénario écrit à l'avance.
"""

from __future__ import annotations

import logging
import sys

from langchain_core.messages import AIMessage, HumanMessage

from .config import configure_logging
from .graph import get_app

logger = logging.getLogger(__name__)

ETIQUETTES = {
    "chargement_profil": "Lecture du profil (RAG)",
    "planificateur": "Analyse de la demande",
    "garde_fou": "Demande hors périmètre",
    "conseiller": "Raisonnement",
    "outils": "Exécution d'un outil",
    "veilleur": "Veille web sur l'entreprise",
    "redacteur": "Rédaction de la lettre",
    "verificateur": "Contrôle factuel de la lettre",
    "sauvegarde": "Décision d'archivage",
    "archiviste": "Archivage dans Notion",
}


def executer(app, historique: list) -> list:
    etat_final: dict = {}
    for evenement in app.stream({"messages": historique}, stream_mode="updates"):
        for noeud, maj in evenement.items():
            print(f"  → {ETIQUETTES.get(noeud, noeud)}")
            etat_final.update(maj or {})
            if maj and maj.get("messages"):
                historique = historique + list(maj["messages"])
    return historique


def main() -> int:
    configure_logging()
    app = get_app()

    print("=" * 60)
    print("  Copilote de Candidature — v3  (tape 'q' pour quitter)")
    print("=" * 60)

    historique: list = []
    while True:
        try:
            saisie = input("\nToi > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir.")
            return 0

        if not saisie:
            continue
        if saisie.lower() in {"q", "quit", "exit"}:
            return 0

        historique.append(HumanMessage(content=saisie))
        try:
            historique = executer(app, historique)
        except Exception:
            logger.exception("Erreur pendant l'exécution du graphe")
            print("\n[Erreur] L'agent n'a pas pu traiter la demande. Voir les logs.")
            continue

        derniere = next(
            (m for m in reversed(historique) if isinstance(m, AIMessage)),
            None,
        )
        print(f"\nCopilote >\n{derniere.content if derniere else '(pas de réponse)'}")


if __name__ == "__main__":
    sys.exit(main())
