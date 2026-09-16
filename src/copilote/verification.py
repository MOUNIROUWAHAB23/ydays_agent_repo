"""Détection déterministe des inventions dans une lettre générée.

Pourquoi ne pas confier cette tâche au LLM ? Parce que c'est le même modèle qui
vient d'inventer : lui demander de s'auto-évaluer donne un juge aussi peu fiable
que le rédacteur. La détection est donc purement lexicale — reproductible,
instantanée, testable — et le LLM n'intervient que pour la réécriture, une fois
les violations identifiées.

Deux familles de violations sont détectées :

1. **Technologie revendiquée sans support** : un terme technique apparaît dans
   la lettre alors qu'il est absent du profil du candidat. C'est le mode
   d'échec principal observé — le modèle recopie la liste de compétences de
   l'offre en se l'attribuant.
2. **Chiffre sur l'entreprise** : pourcentage, effectif, montant. Ces valeurs
   proviennent d'une veille web résumée par le modèle et sont fréquemment
   fausses. Le coût d'un chiffre erroné dans une candidature est disproportionné.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Lexique                                                                      #
# --------------------------------------------------------------------------- #
# Termes surveillés : si l'un d'eux apparaît dans la lettre, il DOIT figurer
# dans le profil. La liste couvre les technologies que les offres data listent
# le plus souvent et que le modèle est tenté de recopier.
TECHNOLOGIES = [
    # Big data / traitement distribué
    "Spark", "PySpark", "Hadoop", "Cloudera", "Hive", "HQL", "Kafka", "Flink",
    "Databricks", "Snowflake", "BigQuery", "Redshift", "Dataproc", "HDFS",
    "MapReduce", "Impala", "Presto", "Trino", "Delta Lake", "Iceberg",
    # Langages
    "Python", "Java", "Scala", "Golang", "Rust", "PHP", "Ruby", "C++", "C#",
    "SQL", "Bash", "Shell", "R",
    # Cloud
    "AWS", "Azure", "GCP", "S3", "RDS", "EC2", "IAM", "Lambda", "Glue",
    "Athena", "EMR", "Kubernetes", "Terraform", "Ansible", "OpenShift",
    # Data engineering
    "Airflow", "dbt", "Talend", "Informatica", "NiFi", "Dagster", "Prefect",
    "Luigi",
    # Bases de données
    "PostgreSQL", "MySQL", "MongoDB", "Oracle", "Cassandra", "Redis",
    "Elasticsearch", "Neo4j", "SQL Server",
    # BI
    "Power BI", "PowerBI", "Tableau", "Qlik", "Looker", "Metabase",
    "Superset", "Streamlit",
    # IA / ML
    "TensorFlow", "PyTorch", "Scikit-learn", "Keras", "XGBoost", "MLflow",
    "Kubeflow", "LangChain", "LangGraph", "ChromaDB", "Ollama", "Llama",
    "Mistral", "RAG", "MCP", "Hugging Face", "Pandas", "NumPy",
    # DevOps / outils
    "Docker", "Git", "GitLab", "Jenkins", "Linux", "FastAPI", "Django",
    "Flask", "Swagger", "OpenAPI", "pytest", "Grafana", "Prometheus",
]

# Termes tolérés même absents du profil : ce sont des concepts de l'offre que
# la lettre peut légitimement nommer sans les revendiquer comme acquis.
CONCEPTS_TOLERES = {"dora", "devops", "mco", "moe", "ci/cd", "agile", "scrum", "mistral", "mcp", "model context protocol",}

# Équivalences : un terme de la lettre est couvert si l'un de ses synonymes
# figure dans le profil. Sans cela, « PowerBI » serait signalé alors que le
# profil dit « Power BI », et « Shell » alors que le profil dit « Bash ».
SYNONYMES: dict[str, tuple[str, ...]] = {
    "PowerBI": ("Power BI",),
    "Power BI": ("PowerBI",),
    "Shell": ("Bash", "Linux"),
    "Bash": ("Shell",),
    "PySpark": ("Spark",),
    "Scikit-learn": ("sklearn", "Scikit learn"),
    "Llama": ("Ollama", "Llama 3.1"),
    "SQL Server": ("MSSQL",),
    "Hugging Face": ("HuggingFace",),
}

# Chiffres : pourcentages, effectifs, montants, durées d'expérience.
# Une technologie absente du profil peut être nommée honnêtement si elle est
# présentée comme un objectif d'apprentissage — ce qui est le propos même d'une
# alternance. On tolère alors la mention.
MARQUEURS_APPRENTISSAGE = (
    "decouvrir", "apprendre", "me former", "monter en competence",
    "montee en competence", "souhaite acquerir", "envie d'apprendre",
    "curieux de", "formation", "approfondir", "developper mes competences",
)
FENETRE_APPRENTISSAGE = 120  # caractères avant la mention

MOTIFS_CHIFFRES = [
    (re.compile(r"\b\d+(?:[.,]\d+)?\s*%"), "pourcentage"),
    (re.compile(r"\b\d[\d\s.,]*\s*(?:collaborateur|salarié|employé|effectif)s?\b", re.I),
     "effectif"),
    (re.compile(r"\b\d[\d\s.,]*\s*(?:milliard|million|md|m€|k€)\b", re.I), "montant"),
    # Apostrophe droite, typographique ou simple espace : le modèle varie.
    (re.compile(
        r"\b(?:plus de\s+|environ\s+)?\d+\s*ans?\s+d\s*['’e]?\s*(?:expérience|expertise)",
        re.I,
    ), "durée d'expérience"),
]


# --------------------------------------------------------------------------- #
# Normalisation                                                                #
# --------------------------------------------------------------------------- #
def normaliser(texte: str) -> str:
    """Minuscules, sans accents : rend la comparaison insensible à la casse.

    « PostgreSQL » dans la lettre doit correspondre à « postgresql » dans le
    profil, et « Scikit-Learn » à « scikit-learn ».
    """
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return texte.lower()


def _present(terme: str, texte_normalise: str) -> bool:
    """Cherche un terme en respectant les frontières de mots.

    Sans frontières, « R » matcherait n'importe quelle lettre R et « SQL »
    matcherait à l'intérieur de « PostgreSQL » — ce qui masquerait justement
    l'invention qu'on cherche à détecter.
    """
    motif = r"(?<![\w-])" + re.escape(normaliser(terme)) + r"(?![\w-])"
    return re.search(motif, texte_normalise) is not None


def _en_contexte_apprentissage(terme: str, texte_normalise: str) -> bool:
    """Vrai si toutes les mentions du terme sont formulées comme un souhait.

    « Je souhaite découvrir Cloudera en alternance » est honnête ; « mes
    compétences en Cloudera » ne l'est pas. On regarde la portion de phrase qui
    précède chaque mention.
    """
    motif = r"(?<![\w-])" + re.escape(normaliser(terme)) + r"(?![\w-])"
    mentions = list(re.finditer(motif, texte_normalise))
    if not mentions:
        return False

    for mention in mentions:
        debut = max(0, mention.start() - FENETRE_APPRENTISSAGE)
        amont = texte_normalise[debut : mention.start()]
        # On ne remonte pas au-delà de la phrase précédente.
        amont = amont.rsplit(".", 1)[-1]
        if not any(marqueur in amont for marqueur in MARQUEURS_APPRENTISSAGE):
            return False  # au moins une mention est une revendication
    return True


# --------------------------------------------------------------------------- #
# Rapport                                                                      #
# --------------------------------------------------------------------------- #
@dataclass
class Violation:
    type: str          # "technologie" | "chiffre"
    valeur: str
    explication: str

    def __str__(self) -> str:
        return f"[{self.type}] {self.valeur} — {self.explication}"


@dataclass
class RapportVerification:
    violations: list[Violation]

    @property
    def conforme(self) -> bool:
        return not self.violations

    @property
    def technologies_fautives(self) -> list[str]:
        return [v.valeur for v in self.violations if v.type == "technologie"]

    def consignes(self) -> str:
        """Instructions de correction à injecter dans le prompt de réécriture."""
        return "\n".join(f"- {v}" for v in self.violations)


# --------------------------------------------------------------------------- #
# Vérification                                                                 #
# --------------------------------------------------------------------------- #
def verifier_lettre(lettre: str, profil: str) -> RapportVerification:
    """Compare la lettre au profil et retourne la liste des violations."""
    if not lettre.strip():
        return RapportVerification([])

    lettre_norm = normaliser(lettre)
    profil_norm = normaliser(profil or "")
    violations: list[Violation] = []

    # 1. Technologies revendiquées sans support dans le profil
    for techno in TECHNOLOGIES:
        if normaliser(techno) in CONCEPTS_TOLERES:
            continue
        if not _present(techno, lettre_norm):
            continue
        # Le terme est couvert s'il figure dans le profil, directement ou via
        # un synonyme.
        variantes = (techno, *SYNONYMES.get(techno, ()))
        if any(_present(v, profil_norm) for v in variantes):
            continue
        # Absent du profil : acceptable seulement si présenté comme un souhait.
        if not _en_contexte_apprentissage(techno, lettre_norm):
            violations.append(
                Violation(
                    type="technologie",
                    valeur=techno,
                    explication=(
                        f"« {techno} » n'apparaît pas dans le profil du candidat : "
                        "cette compétence ne peut pas être revendiquée."
                    ),
                )
            )

    # 2. Chiffres sur l'entreprise
    for motif, libelle in MOTIFS_CHIFFRES:
        for trouve in motif.findall(lettre):
            extrait = trouve if isinstance(trouve, str) else str(trouve)
            violations.append(
                Violation(
                    type="chiffre",
                    valeur=extrait.strip(),
                    explication=(
                        f"Donnée chiffrée ({libelle}) non vérifiable : "
                        "elle doit être supprimée de la lettre."
                    ),
                )
            )

    return RapportVerification(violations)
