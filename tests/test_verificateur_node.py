"""Nœud vérificateur : boucle de correction bornée, pas d'archivage silencieux."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from copilote.config import settings
from copilote.graph import nodes

PROFIL = "Python, Airflow, AWS, Docker, LangGraph, ChromaDB"


def _llm_repondant(contenu):
    faux = MagicMock()
    faux.invoke.return_value = AIMessage(content=contenu)
    return lambda temperature=0.0: faux


def test_lettre_conforme_est_publiee():
    lettre = "J'utilise Airflow et Docker sur AWS. " * 10
    sortie = nodes.noeud_verificateur({"lettre": lettre, "profil": PROFIL, "corrections": 0})
    assert sortie["violations"] == []
    assert isinstance(sortie["messages"][0], AIMessage)


def test_lettre_fautive_declenche_une_correction(monkeypatch):
    monkeypatch.setattr(nodes, "get_llm", _llm_repondant("Version corrigée sans Spark."))
    sortie = nodes.noeud_verificateur(
        {"lettre": "Je maîtrise Spark et Hadoop.", "profil": PROFIL, "corrections": 0}
    )
    assert sortie["corrections"] == 1
    assert sortie["lettre"] == "Version corrigée sans Spark."
    assert "messages" not in sortie  # rien n'est publié tant que ce n'est pas conforme


def test_abandon_apres_le_plafond_de_corrections():
    sortie = nodes.noeud_verificateur(
        {
            "lettre": "Je maîtrise Spark.",
            "profil": PROFIL,
            "corrections": settings.max_corrections,
        }
    )
    assert sortie["lettre_conforme"] is False
    assert "Spark" in sortie["messages"][0].content


def test_routeur_boucle_tant_quil_reste_des_violations():
    assert nodes.routeur_verification({"violations": ["[technologie] Spark"]}) == "verificateur"


def test_routeur_passe_a_la_suite_si_conforme():
    assert nodes.routeur_verification({"violations": []}) == "suite"


def test_routeur_arrete_tout_si_abandon():
    etat = {"violations": ["x"], "lettre_conforme": False}
    assert nodes.routeur_verification(etat) == "fin"


def test_lettre_non_conforme_nest_jamais_archivee():
    """Garantie de bout en bout : abandon => pas de passage par l'archiviste."""
    etat = {
        "lettre": "Je maîtrise Spark.",
        "profil": PROFIL,
        "corrections": settings.max_corrections,
    }
    sortie = nodes.noeud_verificateur(etat)
    assert nodes.routeur_verification({**etat, **sortie}) == "fin"
