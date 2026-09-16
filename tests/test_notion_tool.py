"""L'outil Notion ne doit jamais perdre de contenu ni faire tomber le graphe."""

from unittest.mock import MagicMock

import pytest

from copilote.tools import notion as notion_tool


def test_decoupage_respecte_la_limite_notion(lettre_longue):
    morceaux = notion_tool.decouper_texte(lettre_longue)
    assert morceaux, "une lettre non vide doit produire au moins un bloc"
    assert all(len(m) <= notion_tool.NOTION_TEXT_LIMIT for m in morceaux)


def test_decoupage_ne_perd_pas_de_contenu(lettre_longue):
    reconstitue = "".join(notion_tool.decouper_texte(lettre_longue)).replace("\n", "")
    assert reconstitue == lettre_longue.replace("\n", "")


def test_texte_court_reste_en_un_seul_bloc():
    texte = "Bonjour,\n\nJe candidate.\n\nCordialement."
    assert notion_tool.decouper_texte(texte) == [texte]


def test_texte_vide():
    assert notion_tool.decouper_texte("") == []


def test_blocs_commencent_par_un_titre(lettre_longue):
    blocs = notion_tool.construire_blocs(lettre_longue)
    assert blocs[0]["type"] == "heading_2"
    assert all(b["type"] in {"heading_2", "paragraph"} for b in blocs)


def test_lien_offre_absent_nest_pas_envoye():
    props = notion_tool.construire_proprietes("Doctolib", "Data Engineer")
    assert "Lien" not in props


def test_lien_offre_present_est_envoye():
    props = notion_tool.construire_proprietes("Doctolib", "Data Engineer", "https://x.fr/o/1")
    assert props["Lien"]["url"] == "https://x.fr/o/1"


def test_refus_si_lettre_trop_courte():
    resultat = notion_tool.archiver_candidature.invoke(
        {"entreprise": "Doctolib", "poste": "Data Engineer", "lettre_motivation": "la lettre"}
    )
    assert "Refus" in resultat


def test_echec_api_ne_leve_pas_dexception(monkeypatch, lettre_longue):
    client = MagicMock()
    client.pages.create.side_effect = RuntimeError("401 unauthorized")
    monkeypatch.setattr(notion_tool, "_client", lambda: client)

    resultat = notion_tool.archiver_candidature.invoke(
        {"entreprise": "X", "poste": "Y", "lettre_motivation": lettre_longue}
    )
    assert "Échec" in resultat  # message exploitable par l'agent, pas un crash


def test_succes_appelle_lapi_une_fois(monkeypatch, lettre_longue):
    client = MagicMock()
    monkeypatch.setattr(notion_tool, "_client", lambda: client)

    resultat = notion_tool.archiver_candidature.invoke(
        {"entreprise": "Doctolib", "poste": "Data Engineer", "lettre_motivation": lettre_longue}
    )
    assert client.pages.create.call_count == 1
    assert "archivée" in resultat
