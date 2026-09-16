"""Nœuds testés avec un LLM et un RAG simulés."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from copilote.graph import nodes


def _llm_repondant(contenu: str):
    faux = MagicMock()
    faux.invoke.return_value = AIMessage(content=contenu)
    return lambda temperature=0.0: faux


def test_planificateur_extrait_le_plan(monkeypatch):
    monkeypatch.setattr(
        nodes,
        "get_llm",
        _llm_repondant(
            '{"intention":"candidature","entreprise":"Doctolib",'
            '"poste":"Data Engineer","lien_offre":"","sauvegarder":true}'
        ),
    )
    etat = {"messages": [HumanMessage(content="postuler chez Doctolib")]}
    plan = nodes.noeud_planificateur(etat)

    assert plan["intention"] == "candidature"
    assert plan["entreprise"] == "Doctolib"
    assert plan["sauvegarder"] is True
    assert plan["iterations"] == 0


def test_planificateur_retombe_sur_conseil_si_sortie_illisible(monkeypatch):
    monkeypatch.setattr(nodes, "get_llm", _llm_repondant("je n'ai pas compris"))
    etat = {"messages": [HumanMessage(content="?")]}
    assert nodes.noeud_planificateur(etat)["intention"] == "conseil"


def test_candidature_sans_entreprise_bascule_en_conseil(monkeypatch):
    monkeypatch.setattr(
        nodes, "get_llm", _llm_repondant('{"intention":"candidature","entreprise":""}')
    )
    etat = {"messages": [HumanMessage(content="je veux postuler quelque part")]}
    assert nodes.noeud_planificateur(etat)["intention"] == "conseil"


def test_profil_nest_pas_recharge_sil_existe(monkeypatch):
    appels = []
    monkeypatch.setattr(nodes, "retrieve_profile", lambda q: appels.append(q) or "ctx")
    assert nodes.noeud_profil({"profil": "déjà là", "messages": []}) == {}
    assert appels == []


def test_profil_absorbe_une_panne_du_rag(monkeypatch):
    def boom(_):
        raise ConnectionError("chroma down")

    monkeypatch.setattr(nodes, "retrieve_profile", boom)
    etat = {"messages": [HumanMessage(content="mes compétences ?")]}
    assert nodes.noeud_profil(etat) == {"profil": ""}


def test_noeud_outils_renvoie_un_toolmessage_par_appel(monkeypatch):
    outil = MagicMock()
    outil.invoke.return_value = "résultat"
    monkeypatch.setattr(nodes, "TOOLS_BY_NAME", {"recherche_entreprise": outil})

    message = AIMessage(
        content="",
        tool_calls=[{"name": "recherche_entreprise", "args": {"query": "X"}, "id": "abc"}],
    )
    sortie = nodes.noeud_outils({"messages": [message]})

    assert len(sortie["messages"]) == 1
    assert isinstance(sortie["messages"][0], ToolMessage)
    assert sortie["messages"][0].tool_call_id == "abc"


def test_noeud_outils_gere_un_outil_inconnu():
    message = AIMessage(
        content="", tool_calls=[{"name": "outil_fantome", "args": {}, "id": "z"}]
    )
    sortie = nodes.noeud_outils({"messages": [message]})
    assert "inconnu" in sortie["messages"][0].content


def test_noeud_outils_transforme_une_exception_en_message(monkeypatch):
    outil = MagicMock()
    outil.invoke.side_effect = TimeoutError("api lente")
    monkeypatch.setattr(nodes, "TOOLS_BY_NAME", {"recherche_entreprise": outil})

    message = AIMessage(
        content="", tool_calls=[{"name": "recherche_entreprise", "args": {}, "id": "1"}]
    )
    sortie = nodes.noeud_outils({"messages": [message]})
    assert "échoué" in sortie["messages"][0].content
