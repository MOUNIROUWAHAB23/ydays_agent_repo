"""Couche RAG : indexation du profil et récupération de contexte.

Améliorations par rapport à la V1 :
  * ingestion de **tous** les documents de `data/` (CV, rapports de projet,
    portfolio), pas d'un seul PDF codé en dur ;
  * métadonnées de source conservées → l'agent peut citer d'où vient l'info ;
  * réindexation idempotente (la collection est recréée, pas dupliquée) ;
  * `k` configurable et suffisamment large pour couvrir un CV entier.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import settings
from .llm import get_embeddings

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md"}


def _load_file(path: Path) -> list[Document]:
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path)).load()
    return TextLoader(str(path), encoding="utf-8").load()


def load_documents(directory: Path | None = None) -> list[Document]:
    """Charge tous les documents supportés d'un répertoire."""
    directory = directory or settings.documents_dir
    if not directory.exists():
        raise FileNotFoundError(f"Répertoire de documents introuvable : {directory}")

    documents: list[Document] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        try:
            loaded = _load_file(path)
        except Exception:  # un document illisible ne doit pas casser l'ingestion
            logger.exception("Document ignoré (lecture impossible) : %s", path.name)
            continue
        for doc in loaded:
            doc.metadata["source_file"] = path.name
        documents.extend(loaded)
        logger.info("Chargé : %s (%d page(s))", path.name, len(loaded))

    if not documents:
        raise FileNotFoundError(
            f"Aucun document exploitable dans {directory} "
            f"(extensions acceptées : {', '.join(sorted(SUPPORTED_SUFFIXES))})"
        )
    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    logger.info("Découpage : %d chunks (taille=%d)", len(chunks), settings.chunk_size)
    return chunks


def build_index(directory: Path | None = None) -> int:
    """(Ré)indexe le profil dans ChromaDB. Retourne le nombre de chunks indexés.

    NB : `Chroma.persist()` n'existe plus depuis langchain-chroma >= 0.1,
    la persistance est automatique quand `persist_directory` est fourni.
    """
    documents = load_documents(directory)
    chunks = chunk_documents(documents)

    store = get_vector_store()
    store.reset_collection()  # ingestion idempotente : pas de doublons
    store.add_documents(chunks)
    logger.info("Index prêt : %d chunks dans %s", len(chunks), settings.chroma_dir)
    return len(chunks)


def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=settings.collection_name,
        persist_directory=str(settings.chroma_dir),
        embedding_function=get_embeddings(),
    )


def retrieve_profile(query: str, k: int | None = None) -> str:
    """Retourne le contexte du profil pertinent pour la requête.

    Le texte est annoté par fichier source pour que le rédacteur puisse
    s'appuyer sur des éléments traçables.
    """
    k = k or settings.retrieval_k
    docs = get_vector_store().similarity_search(query, k=k)
    if not docs:
        logger.warning("Aucun chunk de profil récupéré pour : %r", query[:60])
        return ""

    logger.info("RAG : %d chunks récupérés", len(docs))
    blocs = [
        f"[source: {d.metadata.get('source_file', 'inconnu')}]\n{d.page_content.strip()}"
        for d in docs
    ]
    return "\n\n".join(blocs)
