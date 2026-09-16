"""Les nœuds du graphe d'état.

Chaque nœud a une responsabilité unique et renvoie une mise à jour partielle de
l'état. Aucun nœud ne fait de `print` : tout passe par le logger, ce qui permet
de brancher indifféremment une CLI, Streamlit ou des tests.
"""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from ..config import settings
from ..llm import get_llm
from ..parsing import extraire_json
from ..rag import retrieve_profile
from ..verification import verifier_lettre
from ..tools import TOOLS, TOOLS_BY_NAME, archiver_candidature, recherche_entreprise
from . import prompts
from .state import AgentState

logger = logging.getLogger(__name__)

INTENTIONS_VALIDES = {"candidature", "conseil", "hors_sujet"}


def _derniere_demande(state: AgentState) -> str:
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


# --------------------------------------------------------------------------- #
# 1. Profil — RAG                                                              #
# --------------------------------------------------------------------------- #
def noeud_profil(state: AgentState) -> dict:
    """Récupère le contexte pertinent du profil (CV, projets) dans ChromaDB."""
    if state.get("profil"):
        return {}  # déjà chargé sur un tour précédent : on évite un appel inutile

    demande = _derniere_demande(state)
    try:
        profil = retrieve_profile(demande)
    except Exception:
        logger.exception("RAG indisponible")
        profil = ""
    return {"profil": profil}


# --------------------------------------------------------------------------- #
# 2. Planificateur — classification + extraction structurée                    #
# --------------------------------------------------------------------------- #
def noeud_planificateur(state: AgentState) -> dict:
    """Classe la demande et extrait entreprise / poste / intention de sauvegarde.

    Le routage est confié à un appel LLM dédié à température 0 et à sortie JSON
    plutôt qu'au tool calling natif : sur un modèle 8B local, le tool calling
    échoue trop souvent pour porter seul l'orchestration.
    """
    demande = _derniere_demande(state)
    reponse = get_llm(temperature=0.0).invoke(
        [SystemMessage(content=prompts.PLANIFICATEUR.format(demande=demande))]
    )
    plan = extraire_json(str(reponse.content))

    intention = str(plan.get("intention", "")).strip().lower()
    if intention not in INTENTIONS_VALIDES:
        logger.warning("Intention illisible (%r) → repli sur 'conseil'", intention)
        intention = "conseil"

    resultat = {
        "intention": intention,
        "entreprise": str(plan.get("entreprise", "") or "").strip(),
        "poste": str(plan.get("poste", "") or "").strip(),
        "lien_offre": str(plan.get("lien_offre", "") or "").strip(),
        "sauvegarder": bool(plan.get("sauvegarder", False)),
        "offre": demande,
        "iterations": 0,
    }

    # Une "candidature" sans entreprise identifiable n'est pas actionnable.
    if resultat["intention"] == "candidature" and not resultat["entreprise"]:
        logger.info("Candidature sans entreprise identifiée → bascule en conseil")
        resultat["intention"] = "conseil"

    logger.info(
        "Plan : intention=%s entreprise=%r poste=%r sauvegarder=%s",
        resultat["intention"],
        resultat["entreprise"],
        resultat["poste"],
        resultat["sauvegarder"],
    )
    return resultat


# --------------------------------------------------------------------------- #
# 3. Garde-fou — hors sujet                                                    #
# --------------------------------------------------------------------------- #
def noeud_garde_fou(state: AgentState) -> dict:
    """Refus déterministe : ne consomme pas d'appel LLM."""
    logger.info("Demande hors périmètre : refus")
    return {"messages": [AIMessage(content=prompts.REFUS_HORS_SUJET)]}


# --------------------------------------------------------------------------- #
# 4. Conseiller — boucle ReAct avec tool calling natif                         #
# --------------------------------------------------------------------------- #
def noeud_conseiller(state: AgentState) -> dict:
    """Répond aux questions de stratégie / profil, avec accès aux outils."""
    systeme = prompts.CONSEILLER.format(profil=state.get("profil") or "(profil indisponible)")
    llm = get_llm(temperature=0.2).bind_tools(TOOLS)
    reponse = llm.invoke([SystemMessage(content=systeme)] + list(state.get("messages", [])))
    return {"messages": [reponse], "iterations": state.get("iterations", 0) + 1}


def noeud_outils(state: AgentState) -> dict:
    """Exécute les outils demandés et renvoie un ToolMessage par appel.

    Toujours un ToolMessage par `tool_call` : c'est ce que le format de
    conversation exige. Une exception dans un outil devient un message d'erreur
    exploitable par le modèle, pas un crash du graphe.
    """
    messages = state.get("messages", [])
    dernier = messages[-1] if messages else None
    appels = getattr(dernier, "tool_calls", None) or []

    sorties: list[ToolMessage] = []
    for appel in appels:
        nom = appel.get("name", "")
        outil = TOOLS_BY_NAME.get(nom)
        if outil is None:
            contenu = f"Outil inconnu : {nom}."
            logger.warning(contenu)
        else:
            try:
                contenu = str(outil.invoke(appel.get("args", {})))
            except Exception as exc:
                logger.exception("Échec de l'outil %s", nom)
                contenu = f"L'outil {nom} a échoué ({type(exc).__name__}: {exc})."
        sorties.append(ToolMessage(content=contenu, tool_call_id=appel.get("id", "")))

    return {"messages": sorties}


# --------------------------------------------------------------------------- #
# 5. Veilleur — appel d'outil déterministe                                     #
# --------------------------------------------------------------------------- #
def noeud_veilleur(state: AgentState) -> dict:
    """Interroge le web sur l'entreprise ciblée avant la rédaction."""
    entreprise = state.get("entreprise", "")
    requete = f"{entreprise} actualités 2026 recrutement données"
    veille = recherche_entreprise.invoke({"query": requete})
    return {"veille": veille}


# --------------------------------------------------------------------------- #
# 6. Rédacteur — agent d'écriture dédié                                        #
# --------------------------------------------------------------------------- #
def noeud_redacteur(state: AgentState) -> dict:
    """Rédige la lettre. Température plus haute que le routage : on veut du texte."""
    systeme = prompts.REDACTEUR.format(
        profil=state.get("profil") or "(profil indisponible)",
        veille=state.get("veille") or "(aucune information externe disponible)",
        offre=state.get("offre") or "(aucun texte d'offre fourni)",
        poste=state.get("poste") or "poste visé",
        entreprise=state.get("entreprise", ""),
        candidat_nom=settings.candidat_nom or "le candidat",
    )
    reponse = get_llm(temperature=0.3).invoke([SystemMessage(content=systeme)])
    lettre = str(reponse.content).strip()
    logger.info("Lettre rédigée (%d caractères)", len(lettre))
    # La lettre n'est pas encore publiée dans `messages` : elle doit d'abord
    # passer le contrôle factuel du nœud `verificateur`.
    return {"lettre": lettre, "corrections": 0, "violations": []}


# --------------------------------------------------------------------------- #
# 8. Archiviste — écriture Notion                                              #
# --------------------------------------------------------------------------- #
def noeud_archiviste(state: AgentState) -> dict:
    """Enregistre la candidature dans Notion (lettre complète, non tronquée)."""
    resultat = archiver_candidature.invoke(
        {
            "entreprise": state.get("entreprise", ""),
            "poste": state.get("poste", ""),
            "lettre_motivation": state.get("lettre", ""),
            "lien_offre": state.get("lien_offre", ""),
        }
    )
    return {"messages": [AIMessage(content=resultat)]}



# --------------------------------------------------------------------------- #
# 7. Vérificateur — contrôle factuel déterministe + réécriture ciblée          #
# --------------------------------------------------------------------------- #
def noeud_verificateur(state: AgentState) -> dict:
    """Détecte les inventions dans la lettre et la fait corriger si besoin.

    La détection est lexicale (module `verification`), donc reproductible : on
    ne demande pas au modèle qui vient d'inventer de juger sa propre sortie.
    Le LLM n'est sollicité que pour la réécriture, avec la liste précise des
    éléments à retirer.
    """
    lettre = state.get("lettre", "")
    profil = state.get("profil", "")
    rapport = verifier_lettre(lettre, profil)
    tentative = state.get("corrections", 0)

    if rapport.conforme:
        if tentative:
            logger.info("Lettre conforme après %d correction(s)", tentative)
        else:
            logger.info("Lettre conforme dès la première rédaction")
        return {"violations": [], "messages": [AIMessage(content=lettre)]}

    logger.warning(
        "Lettre non conforme (tentative %d) : %d violation(s) — %s",
        tentative + 1,
        len(rapport.violations),
        ", ".join(v.valeur for v in rapport.violations),
    )

    if tentative >= settings.max_corrections:
        # On n'archive jamais une lettre non conforme en silence.
        avertissement = (
            "⚠️ La lettre générée contient encore des affirmations non fondées "
            "après plusieurs tentatives de correction :\n"
            + rapport.consignes()
            + "\n\nElle n'a pas été archivée. Relance la demande ou corrige "
            "manuellement le texte ci-dessous.\n\n---\n\n"
            + lettre
        )
        logger.error("Abandon après %d corrections", tentative)
        return {
            "violations": [str(v) for v in rapport.violations],
            "lettre_conforme": False,
            "messages": [AIMessage(content=avertissement)],
        }

    systeme = prompts.CORRECTION.format(
        profil=profil or "(profil indisponible)",
        lettre=lettre,
        violations=rapport.consignes(),
        candidat_nom=settings.candidat_nom or "le candidat",
    )
    reponse = get_llm(temperature=0.1).invoke([SystemMessage(content=systeme)])
    corrigee = str(reponse.content).strip()

    return {
        "lettre": corrigee,
        "corrections": tentative + 1,
        "violations": [str(v) for v in rapport.violations],
    }


# --------------------------------------------------------------------------- #
# Routeurs                                                                     #
# --------------------------------------------------------------------------- #
def routeur_intention(state: AgentState) -> str:
    intention = state.get("intention", "conseil")
    return {"candidature": "veilleur", "hors_sujet": "garde_fou"}.get(intention, "conseiller")


def routeur_outils(state: AgentState) -> str:
    """Boucle ReAct bornée : coupe si le modèle tourne en rond."""
    if state.get("iterations", 0) >= settings.max_iterations:
        logger.warning("Plafond d'itérations atteint (%d)", settings.max_iterations)
        return "fin"

    messages = state.get("messages", [])
    dernier = messages[-1] if messages else None
    if getattr(dernier, "tool_calls", None):
        return "outils"
    return "fin"


def routeur_verification(state: AgentState) -> str:
    """Boucle bornée : rédaction -> vérification -> correction -> vérification."""
    if state.get("lettre_conforme") is False:
        return "fin"  # abandon signalé à l'utilisateur, pas d'archivage
    if state.get("violations"):
        return "verificateur"  # une correction vient d'être produite, on revalide
    return "suite"


def routeur_sauvegarde(state: AgentState) -> str:
    if state.get("sauvegarder") and state.get("lettre"):
        return "archiviste"
    return "fin"
