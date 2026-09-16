"""Extraction robuste de JSON depuis une sortie de LLM.

Un modèle 8B exécuté en local respecte imparfaitement la consigne « réponds
uniquement en JSON » : il ajoute des préambules, des fences markdown, des
commentaires. Plutôt que d'empiler des `if` dans les nœuds, on isole ici la
tolérance au bruit — et on la teste unitairement.
"""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _candidats(texte: str):
    """Génère les sous-chaînes susceptibles d'être du JSON, du plus probable au moins."""
    texte = texte.strip()
    yield texte
    for bloc in _FENCE.findall(texte):
        yield bloc.strip()
    # Premier objet équilibré rencontré dans le texte
    debut = texte.find("{")
    if debut != -1:
        profondeur = 0
        for i in range(debut, len(texte)):
            if texte[i] == "{":
                profondeur += 1
            elif texte[i] == "}":
                profondeur -= 1
                if profondeur == 0:
                    yield texte[debut : i + 1]
                    break


def extraire_json(texte: str) -> dict:
    """Retourne le premier objet JSON valide trouvé, ou `{}` si aucun.

    Ne lève jamais : un échec de parsing est une situation normale que le
    graphe doit savoir absorber.
    """
    if not texte:
        return {}
    for candidat in _candidats(texte):
        try:
            valeur = json.loads(candidat)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(valeur, dict):
            return valeur
    logger.debug("Aucun JSON exploitable dans : %r", texte[:120])
    return {}
