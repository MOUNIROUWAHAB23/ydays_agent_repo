"""Interface Streamlit.

Différence majeure avec la V1 : les étapes affichées à l'utilisateur sont
émises par `app.stream()` au fur et à mesure de l'exécution. La V1 affichait
« Recherche web… » puis « Envoi Notion… » avec des `time.sleep(1)` *après* que
l'agent ait déjà terminé, y compris quand aucun outil n'avait été appelé.
"""

from __future__ import annotations

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from copilote.cli import ETIQUETTES
from copilote.config import configure_logging, settings
from copilote.graph import get_app

st.set_page_config(page_title="Copilote de Candidature", page_icon="🎯", layout="wide")
configure_logging()


@st.cache_resource
def _app():
    return get_app()


with st.sidebar:
    st.markdown("### Copilote de Candidature")
    st.caption("Agent RAG multi-nœuds · LLM exécuté en local")

    st.markdown("**Stack**")
    st.code(
        f"LLM      : {settings.llm_model} (Ollama)\n"
        f"Embed.   : {settings.embedding_model}\n"
        "Graphe   : LangGraph\n"
        "Vecteurs : ChromaDB\n"
        "Outils   : Tavily · Notion",
        language="text",
    )

    st.markdown("**Services**")
    st.write("Veille web :", "✅" if settings.web_search_enabled else "❌ non configurée")
    st.write("Notion :", "✅" if settings.notion_enabled else "❌ non configuré")

    if st.button("Réinitialiser la session"):
        st.session_state.historique = []
        st.rerun()

st.title("Copilote de Candidature")
st.caption("Analyse ton profil, enquête sur l'entreprise, rédige et archive ta candidature.")

if "historique" not in st.session_state:
    st.session_state.historique = []

for message in st.session_state.historique:
    role = "user" if isinstance(message, HumanMessage) else "assistant"
    with st.chat_message(role):
        st.markdown(message.content)

if prompt := st.chat_input("Ex. : je veux postuler comme Data Engineer chez Doctolib"):
    st.session_state.historique.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Copie de travail : LangGraph itère sur cette liste, on ne la modifie
        # pas pendant le parcours.
        entree = list(st.session_state.historique)
        produits = []

        with st.status("Traitement en cours…", expanded=True) as status:
            try:
                for evenement in _app().stream({"messages": entree}, stream_mode="updates"):
                    for noeud, maj in evenement.items():
                        st.write(ETIQUETTES.get(noeud, noeud))
                        if maj and maj.get("messages"):
                            produits.extend(maj["messages"])
                status.update(label="Terminé", state="complete", expanded=False)
            except Exception as exc:
                status.update(label="Échec", state="error", expanded=True)
                st.exception(exc)   # trace complète affichée dans la page
                produits = []

        st.session_state.historique.extend(produits)

        derniere = next(
            (m for m in reversed(produits) if isinstance(m, AIMessage)),
            None,
        )
        if derniere:
            st.markdown(derniere.content)