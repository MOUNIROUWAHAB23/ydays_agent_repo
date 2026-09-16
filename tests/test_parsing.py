"""Le planificateur dépend entièrement de la robustesse de cet extracteur."""

import pytest

from copilote.parsing import extraire_json


def test_json_pur():
    assert extraire_json('{"intention": "conseil"}') == {"intention": "conseil"}


def test_json_entoure_de_fences_markdown():
    brut = 'Voici le résultat :\n```json\n{"intention": "candidature"}\n```\nVoilà.'
    assert extraire_json(brut)["intention"] == "candidature"


def test_json_noye_dans_du_texte():
    brut = 'Bien sûr ! {"intention": "hors_sujet", "entreprise": ""} J\'espère que ça aide.'
    assert extraire_json(brut)["intention"] == "hors_sujet"


def test_objet_imbrique_conserve():
    brut = 'blabla {"a": {"b": 1}} fin'
    assert extraire_json(brut) == {"a": {"b": 1}}


@pytest.mark.parametrize("brut", ["", "je ne sais pas", "[1, 2, 3]", "{cassé"])
def test_entrees_non_exploitables_renvoient_dict_vide(brut):
    assert extraire_json(brut) == {}
