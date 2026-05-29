import streamlit as st
import time
from langchain_core.messages import HumanMessage
from agent import app as agent_app

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Copilote IA | Stratégie Carrière",
    page_icon="🎯",
    layout="wide"
)

# --- 2. THÈME ET CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    /* Couleur de fond et police globale */
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    
    /* Style du titre innovant */
    .main-title {
        font-size: 3rem !important;
        font-weight: 800;
        background: -webkit-linear-gradient(#00d4ff, #005088);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0rem;
    }
    
    /* Personnalisation de la barre latérale */
    [data-testid="stSidebar"] {
        background-color: #1A1C24;
        border-right: 1px solid #2D3139;
    }
    
    /* Bulles de chat stylisées */
    .stChatMessage {
        border-radius: 15px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #2D3139;
    }
    
    /* Masquer le menu Streamlit par défaut */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 3. BARRE LATÉRALE (Sidebar) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=80)
    st.markdown("### **Copilote de Candidature V1**")
    st.markdown("---")
    st.info("💡 **Conseil :** Soyez précis sur le nom de l'entreprise pour que l'agent puisse trouver les actualités les plus fraîches.")
    
    st.markdown("### **Stack Technique**")
    st.code("Llama 3.1 (Ollama)\nLangGraph\nChromaDB (RAG)\nTavily Web Search\nNotion API", language="text")
    
    if st.button("Réinitialiser la session"):
        st.session_state.messages = []
        st.session_state.historique_langgraph = []
        st.rerun()

# --- 4. EN-TÊTE ---
st.markdown('<h1 class="main-title">Copilote de Candidature</h1>', unsafe_allow_html=True)
st.markdown("##### *L'Intelligence Artificielle au service de votre prochain job.*")
st.write("---")

# --- 5. INITIALISATION MÉMOIRE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.historique_langgraph = []

# --- 6. AFFICHAGE DES MESSAGES ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- 7. CHAT INPUT ET LOGIQUE AGENT ---
if prompt := st.chat_input("Ex: Je veux postuler chez Mistral AI..."):
    
    # A. Affichage utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.historique_langgraph.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    # B. Réponse Assistant avec UX Innovante
    with st.chat_message("assistant"):
        
        # On utilise st.status pour montrer les étapes "en arrière-plan"
        with st.status("⚡ Analyse stratégique en cours...", expanded=True) as status:
            
            st.write("📖 Lecture de votre CV (RAG)...")
            # Appel réel de l'agent
            result = agent_app.invoke({
                "messages": st.session_state.historique_langgraph, 
                "contexte_rag": ""
            })
            
            st.write("🔎 Enquête sur le Web (Tavily)...")
            time.sleep(1) # Petit délai pour l'effet visuel
            
            st.write("💾 Rédaction et envoi vers Notion...")
            time.sleep(1)
            
            status.update(label="✅ Opération réussie !", state="complete", expanded=False)

        reponse_finale = result["messages"][-1].content
        st.markdown(reponse_finale)
        
        # Sauvegarde
        st.session_state.messages.append({"role": "assistant", "content": reponse_finale})
        st.session_state.historique_langgraph = result["messages"]