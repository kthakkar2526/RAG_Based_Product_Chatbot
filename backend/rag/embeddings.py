import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

client = chromadb.Client(Settings(
    persist_directory="chroma_store"  # store locally
))
collection = client.get_or_create_collection("notes_rag")
model = SentenceTransformer("all-MiniLM-L6-v2")

def embed_text(text):
    return model.encode([text])[0].tolist()

def upsert_note(note_id, text, timestamp):
    embedding = embed_text(text)
    collection.upsert(
        documents=[text],
        embeddings=[embedding],
        ids=[str(note_id)],
        metadatas=[{"timestamp": timestamp}]
    )

def retrieve_similar_notes(query, top_k=3):
    embedding = embed_text(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    return results