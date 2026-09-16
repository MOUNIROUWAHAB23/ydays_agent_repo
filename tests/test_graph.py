"""Vérifie que le graphe compile et expose bien la topologie attendue."""

from copilote.graph import construire_graphe

NOEUDS_ATTENDUS = {
    "chargement_profil",
    "planificateur",
    "garde_fou",
    "conseiller",
    "outils",
    "veilleur",
    "redacteur",
    "archiviste",
}


def test_le_graphe_compile():
    assert construire_graphe() is not None


def test_tous_les_noeuds_sont_presents():
    graphe = construire_graphe().get_graph()
    assert NOEUDS_ATTENDUS.issubset(set(graphe.nodes))


def test_le_graphe_contient_bien_un_cycle():
    """conseiller -> outils -> conseiller : le graphe n'est pas linéaire."""
    aretes = {(a.source, a.target) for a in construire_graphe().get_graph().edges}
    assert ("conseiller", "outils") in aretes
    assert ("outils", "conseiller") in aretes

def test_la_lettre_passe_par_le_controle_avant_archivage():
    """Aucun chemin ne doit relier directement le rédacteur à l'archiviste."""
    aretes = {(a.source, a.target) for a in construire_graphe().get_graph().edges}
    assert ("redacteur", "verificateur") in aretes
    assert ("redacteur", "archiviste") not in aretes