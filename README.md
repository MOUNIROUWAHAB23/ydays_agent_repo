# Copilote de Candidature

Agent IA multi-outils qui automatise la recherche d'emploi : il lit votre profil (RAG), enquête sur l'entreprise ciblée, rédige une lettre de motivation sur mesure — avec un contrôle factuel qui bloque les inventions — puis l'archive dans Notion. LLM exécuté entièrement en local via Ollama.

## Architecture

Graphe d'état [LangGraph](https://github.com/langchain-ai/langgraph), à rôles spécialisés :

```
Profil (RAG) → Planificateur ─┬─ hors_sujet   → Garde-fou
                                ├─ conseil      → Conseiller ⇄ Outils
                                └─ candidature  → Veilleur → Rédacteur → Vérificateur → Archiviste
```

- **Planificateur** — classe la demande et extrait entreprise/poste en JSON structuré (le tool-calling natif est trop peu fiable sur un LLM 8B local pour porter seul l'orchestration)
- **Conseiller** — répond aux questions de stratégie, avec accès aux outils (boucle ReAct bornée)
- **Veilleur / Rédacteur** — recherche web (Tavily) puis rédaction de la lettre
- **Vérificateur** — détecte les affirmations non fondées dans la lettre par comparaison lexicale au profil, et déclenche jusqu'à 2 corrections avant archivage
- **Archiviste** — enregistre la candidature complète dans Notion (lettre non tronquée)

## Stack

Python · LangGraph · LangChain · Ollama (Llama 3.1 + nomic-embed-text) · ChromaDB · Tavily · Notion API · Streamlit · Docker · pytest

## Installation

**Prérequis :** Python 3.11+, et [Ollama](https://ollama.com/) lancé avec les modèles suivants :

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

**Configuration :**

```bash
cp .env.example .env          # renseignez vos clés (Tavily, Notion)
pip install -r requirements-dev.txt
```

**Indexation du profil** (CV, rapports de projet, portfolio en `.pdf` / `.md` / `.txt` dans `data/`) :

```bash
make ingest
```

## Utilisation

```bash
make run     # interface web (Streamlit) → localhost:8501
make cli     # interface en ligne de commande
make test    # suite de tests (sans réseau ni Ollama)
```

Avec Docker : `docker compose up` (interface web) ou `docker compose --profile tools run --rm ingest` (indexation).

## Structure

| Chemin | Rôle |
|---|---|
| `src/copilote/graph/` | Graphe LangGraph : nœuds, routeurs, prompts |
| `src/copilote/rag.py` | Indexation et recherche dans ChromaDB |
| `src/copilote/tools/` | Outils : recherche web (Tavily), archivage (Notion) |
| `src/copilote/verification.py` | Contrôle factuel de la lettre générée |
| `src/copilote/config.py` | Configuration centralisée, validée au démarrage |
| `scripts/ingest.py` | Point d'entrée d'indexation |
| `tests/` | Suite pytest |

## Confidentialité

Le LLM et les embeddings tournent entièrement en local via Ollama : le profil et les échanges ne quittent jamais la machine. Seule la requête de veille sur l'entreprise passe par l'API Tavily.
