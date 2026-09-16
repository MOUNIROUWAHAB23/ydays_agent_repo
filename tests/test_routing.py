"""Le routage est la pièce critique du graphe : il est testé sans LLM."""

from langchain_core.messages import AIMessage, HumanMessage

from copilote.config import settings
from copilote.graph import nodes


def _ai_avec_outil():
    return AIMessage(
        content="",
        tool_calls=[{"name": "recherche_entreprise", "args": {"query": "Doctolib"}, "id": "1"}],
    )


def test_intention_candidature_va_vers_la_veille():
    assert nodes.routeur_intention({"intention": "candidature"}) == "veilleur"


def test_intention_hors_sujet_va_vers_le_garde_fou():
    assert nodes.routeur_intention({"intention": "hors_sujet"}) == "garde_fou"


def test_intention_inconnue_retombe_sur_le_conseiller():
    assert nodes.routeur_intention({"intention": "n'importe quoi"}) == "conseiller"
    assert nodes.routeur_intention({}) == "conseiller"


def test_appel_doutil_declenche_le_noeud_outils():
    etat = {"messages": [_ai_avec_outil()], "iterations": 1}
    assert nodes.routeur_outils(etat) == "outils"


def test_reponse_textuelle_termine_le_graphe():
    etat = {"messages": [AIMessage(content="Voici mon conseil.")], "iterations": 1}
    assert nodes.routeur_outils(etat) == "fin"


def test_texte_mentionnant_un_outil_ne_declenche_pas_de_boucle():
    """Régression V1 : le routeur bouclait dès que le mot apparaissait dans le texte."""
    etat = {
        "messages": [AIMessage(content="J'utiliserais l'outil recherche_entreprise ici.")],
        "iterations": 1,
    }
    assert nodes.routeur_outils(etat) == "fin"


def test_plafond_ditérations_coupe_la_boucle():
    etat = {"messages": [_ai_avec_outil()], "iterations": settings.max_iterations}
    assert nodes.routeur_outils(etat) == "fin"


def test_sauvegarde_uniquement_si_demandee_et_lettre_presente():
    assert nodes.routeur_sauvegarde({"sauvegarder": True, "lettre": "x" * 300}) == "archiviste"
    assert nodes.routeur_sauvegarde({"sauvegarder": False, "lettre": "x" * 300}) == "fin"
    assert nodes.routeur_sauvegarde({"sauvegarder": True, "lettre": ""}) == "fin"


def test_garde_fou_repond_sans_appeler_le_llm():
    sortie = nodes.noeud_garde_fou({"messages": [HumanMessage(content="recette de crêpes")]})
    assert isinstance(sortie["messages"][0], AIMessage)
