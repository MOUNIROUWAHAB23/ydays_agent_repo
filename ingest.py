import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
def ingest_documents():
    print("[Ingestion] Chargement du CV...")
    loader = PyPDFLoader("data/GODLIGHT MOUNIROU_CV.pdf") # Assure-toi d'avoir ce dossier et fichier
    documents = loader.load()

    print("[Ingestion] Découpage du texte (Chunking)...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)

    print("[Ingestion] Création des embeddings avec nomic-embed-text...")
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

    
    embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=ollama_url
)
    
    # Sauvegarde dans une base vectorielle locale persistante
    vector_db = Chroma.from_documents(
        documents=chunks, 
        embedding=embeddings, 
        persist_directory="./chroma_db"
    )
    vector_db.persist()
    print("[Ingestion] Terminé ! Base de données vectorielle prête.")

if __name__ == "__main__":
    ingest_documents()