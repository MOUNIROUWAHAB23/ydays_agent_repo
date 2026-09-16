# Audit de la V1 et corrections apportées en V2

Document de travail : ce qui a été trouvé dans la première version, pourquoi
c'était un problème, et ce qui a été fait.

## 1. Sécurité — à traiter en priorité absolue

| Constat | Impact |
|---|---|
| `.env` versionné dans Git avec clé Tavily et token Notion réels | Les clés sont dans l'historique du dépôt. Un dépôt public = compromission immédiate. |
| Aucun `.gitignore` | Rien n'empêchait le commit. |
| `COPY . .` sans `.dockerignore` | Le `.env` était embarqué dans l'image Docker. |
| CV en PDF et index `chroma_db/` versionnés | Données personnelles publiées, et binaires qui gonflent le dépôt. |

**Actions** : révoquer et régénérer les deux clés, purger l'historique Git,
ajouter `.gitignore` / `.dockerignore` / `.env.example`.

## 2. Bugs fonctionnels

| Constat | Correction V2 |
|---|---|
| `vector_db.persist()` supprimé depuis `langchain-chroma >= 0.1` → `AttributeError` en fin d'ingestion | Retiré ; la persistance est automatique avec `persist_directory` |
| `noeud_outils` : variable `res` non affectée si le nom d'outil est inconnu → `UnboundLocalError` | Table `TOOLS_BY_NAME` + message d'erreur renvoyé au modèle |
| Le routeur bascule vers les outils dès que la chaîne `"recherche_entreprise"` apparaît dans le **texte** de la réponse → boucle infinie possible | Routage uniquement sur des `tool_calls` réels, plus compteur d'itérations borné |
| Le fallback renvoyait un `HumanMessage` au lieu d'un `ToolMessage` → historique de conversation incohérent après un appel d'outil | Un `ToolMessage` par `tool_call`, avec `tool_call_id` |
| `lettre_motivation[:2000]` tronque silencieusement la lettre | Découpage en blocs Notion de 1900 caractères, aucune perte |
| `WORKDIR /ydays_project_agent` mais volume monté sur `/app` | Chemins alignés, `PYTHONPATH` défini |
| `operator.add` comme réducteur de messages | `add_messages` de LangGraph (déduplication, appariement AI/Tool) |

## 3. Qualité perçue en entretien

| Constat | Correction V2 |
|---|---|
| L'UI Streamlit affichait « Recherche web… » puis « Envoi Notion… » avec des `time.sleep(1)` **après** l'exécution complète de l'agent, même quand aucun outil n'avait été appelé | Étapes émises par `app.stream()`, donc réelles |
| `requirements.txt` sans aucune version | Bornes de compatibilité + mention du lock |
| Aucun test, alors que `pytest` figure sur le CV | Suite pytest sans réseau ni Ollama |
| Tout dans trois fichiers, `print` mêlés à la logique | Package `src/copilote`, logging structuré |
| Fichier `readme` sans extension → non rendu sur GitHub | `README.md` avec schéma Mermaid |
| RAG : 9 chunks indexés, `k=2` → environ 20 % du CV visible par l'agent | `chunk_size=800`, `k=6`, ingestion de tous les documents de `data/` |
| Température 0.0 y compris pour la rédaction | Température par rôle : 0.0 routage, 0.3 rédaction |
| Prompt système avec fautes visibles en revue de code | Prompts isolés dans `graph/prompts.py`, relus |
| Un seul nœud LLM porte l'ensemble du raisonnement | Rôles distincts : planificateur, conseiller, rédacteur |

## 4. Points restants, volontairement non traités

- Pas de persistance de conversation entre sessions (un `checkpointer` LangGraph
  serait la suite logique).
- Pas de cache sur la veille web.
- Pas d'évaluation automatisée de la qualité des lettres.

Les assumer explicitement en entretien vaut mieux que de les découvrir en direct.
