"""Contrôle factuel : c'est la pièce qui empêche d'envoyer une lettre fausse."""

import pytest

from copilote.verification import verifier_lettre

PROFIL = """
Python, SQL, Java, PHP, Golang.
Pipelines ETL, Airflow (DAGs, scheduler), Data Lake.
AWS (S3, RDS, EC2, IAM), Docker & Docker Compose, Git, Linux / Bash.
RAG, agents, tool calling, LLM local (Ollama), LangGraph, ChromaDB.
PostgreSQL, MySQL, MongoDB. Django REST Framework, FastAPI, pytest.
Pandas, NumPy, Scikit-learn. Power BI, Metabase, Streamlit.
"""


def _valeurs(lettre, profil=PROFIL):
    return {v.valeur for v in verifier_lettre(lettre, profil).violations}


# --- Technologies -------------------------------------------------------- #

@pytest.mark.parametrize("techno", ["Spark", "Hadoop", "Cloudera", "HQL", "Snowflake"])
def test_technologie_absente_du_profil_est_signalee(techno):
    assert techno in _valeurs(f"Je maîtrise {techno} depuis longtemps.")


@pytest.mark.parametrize("techno", ["Python", "Airflow", "LangGraph", "ChromaDB", "Docker"])
def test_technologie_presente_dans_le_profil_est_acceptee(techno):
    assert verifier_lettre(f"J'utilise {techno} au quotidien.", PROFIL).conforme


def test_cas_reel_recopie_de_la_liste_de_loffre():
    """Régression : le modèle recopiait les hard skills de l'offre CDC."""
    lettre = (
        "Mes compétences en Python, Spark, SQL (HQL), Shell, Git, Hadoop, "
        "Cloudera et PowerBI sont parfaitement adaptées à ce poste."
    )
    fautives = _valeurs(lettre)
    assert {"Spark", "Hadoop", "Cloudera", "HQL"} <= fautives
    # Ni Python ni Git ne doivent être signalés : ils sont au profil.
    assert "Python" not in fautives and "Git" not in fautives


def test_synonyme_dans_le_profil_evite_le_faux_positif():
    """« PowerBI » est couvert par « Power BI », « Shell » par « Bash »."""
    assert verifier_lettre("Je fais du PowerBI et du Shell.", PROFIL).conforme


def test_sous_chaine_ne_declenche_pas_de_detection():
    """« SQL » ne doit pas matcher à l'intérieur de « PostgreSQL »."""
    assert verifier_lettre("J'utilise PostgreSQL.", "PostgreSQL uniquement").conforme


def test_insensibilite_a_la_casse_et_aux_accents():
    assert verifier_lettre("j'utilise AIRFLOW", "airflow").conforme


# --- Contexte d'apprentissage --------------------------------------------- #

def test_souhait_dapprentissage_est_tolere():
    lettre = "Je souhaite découvrir Cloudera et monter en compétence sur Spark en alternance."
    assert verifier_lettre(lettre, PROFIL).conforme


def test_revendication_deguisee_reste_detectee():
    lettre = "Je maîtrise Spark. Par ailleurs je souhaite apprendre Spark."
    assert "Spark" in _valeurs(lettre)


# --- Chiffres -------------------------------------------------------------- #

def test_pourcentage_sur_lentreprise_est_signale():
    assert "94%" in _valeurs("J'ai lu que 94% des collaborateurs sont satisfaits.")


@pytest.mark.parametrize(
    "phrase",
    [
        "Avec plus de 3 ans d'expérience",
        "Avec plus de 3 ans d expérience",
        "Avec 5 ans d’expérience",
    ],
)
def test_duree_dexperience_inventee_est_signalee(phrase):
    assert verifier_lettre(phrase, PROFIL).violations


def test_effectif_est_signale():
    assert verifier_lettre("L'entreprise compte 5000 collaborateurs.", PROFIL).violations


# --- Rapport --------------------------------------------------------------- #

def test_lettre_vide_est_conforme():
    assert verifier_lettre("", PROFIL).conforme


def test_consignes_listent_chaque_violation():
    rapport = verifier_lettre("Je maîtrise Spark et Hadoop.", PROFIL)
    consignes = rapport.consignes()
    assert "Spark" in consignes and "Hadoop" in consignes
    assert len(consignes.splitlines()) == len(rapport.violations)


def test_lettre_honnete_complete_passe():
    lettre = (
        "Mon projet d'agent IA repose sur LangGraph, ChromaDB et un LLM exécuté "
        "en local via Ollama. J'ai orchestré des pipelines ETL avec Airflow sur "
        "AWS (S3, RDS, IAM), le tout conteneurisé avec Docker. Je souhaite "
        "découvrir l'écosystème Cloudera en alternance."
    )
    assert verifier_lettre(lettre, PROFIL).conforme
