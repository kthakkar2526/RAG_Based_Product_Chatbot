import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime
from rank_bm25 import BM25Okapi
import re, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "..", "chroma_store")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# ✅ Create or get the collection
collection = chroma_client.get_or_create_collection(name="notes")

# ✅ Load embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def add_note_to_chroma(note_id, text):
    embedding = embedder.encode([text])[0].tolist()
    metadata = {
        "note_id": note_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    print(f"🧠 Adding to Chroma: id={note_id}, text_len={len(text)}")
    collection.add(
        ids=[str(note_id)],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata],
    )
    print(f"Added note {note_id} to Chroma")

    # 🔄 Rebuild BM25 index so hybrid retrieval sees the new note
    load_bm25_index()

    # Add to ChromaDB with explicit IDs
    collection.add(
        ids=[str(note_id)],
        documents=[text],
        embeddings=[embedding],
        metadatas=[metadata]
    )
    print(f"Added note {note_id} to Chroma")

# For testing only — not used by main chatbot
def query_chroma(query_text, top_k=3):
    """
    Returns top matching notes for a query using cosine similarity.
    """
    embedding = embedder.encode([query_text])[0].tolist()
    results = collection.query(
        query_embeddings=[embedding],
        n_results=top_k
    )
    return results


# --- Build BM25 corpus in memory from Chroma ---
docs_store = []
metas_store = []

def load_bm25_index():
    global bm25, docs_store, metas_store
    all_docs = collection.get(limit=999999, include=["documents", "metadatas"])
    docs_store  = all_docs.get("documents", [])
    metas_store = all_docs.get("metadatas", [])
    if not docs_store:
        bm25 = BM25Okapi([[]])  # empty placeholder
        print("ℹ️ BM25 index built with 0 notes.")
        return
    tokenized = [re.findall(r"\w+", doc.lower()) for doc in docs_store]
    bm25 = BM25Okapi(tokenized)
    print(f"✅ BM25 index built with {len(docs_store)} notes.")

load_bm25_index()

# -------------------------------
# HYBRID RETRIEVAL
# -------------------------------
# -------------------------------
# HYBRID RETRIEVAL (with confidence gate)
# -------------------------------
def hybrid_retrieve(query: str, top_k: int = 3,
                    alpha: float = 0.6,          # weight for semantic similarity
                    min_confidence: float = 0.28 # refuse if below this combined score
                   ):
    """
    Hybrid retrieval = semantic (Chroma) + BM25.
    Returns (top_docs, top_metas, debug_info).
    If confidence is low, returns ([], [], {"reason": "..."}).
    """
    if not docs_store:  # no corpus yet
        return [], [], {"reason": "Empty corpus: BM25 has no docs."}

    # --- 0) Prep
    query_tokens = re.findall(r"\w+", query.lower())

    # --- 1) Semantic retrieval (ask Chroma for distances)
    query_emb = embedder.encode([query])[0].tolist()
    sem = collection.query(
        query_embeddings=[query_emb],
        n_results=min(8, max(1, collection.count())),
        include=["documents", "metadatas", "distances"],
    )

    sem_docs   = sem.get("documents", [[]])[0]
    sem_metas  = sem.get("metadatas", [[]])[0]
    sem_dists  = sem.get("distances", [[]])[0]  # cosine distance; lower is better

    # Convert distances -> similarity in [0..1]; guard for weird values
    sem_sims = [max(0.0, min(1.0, 1.0 - d)) for d in sem_dists]

    # --- 2) BM25 retrieval (scores unbounded -> normalize)
    bm25_scores = bm25.get_scores(query_tokens)
    if max(bm25_scores) > 0:
        bm25_norm = [s / max(bm25_scores) for s in bm25_scores]
    else:
        bm25_norm = [0.0] * len(bm25_scores)

    # top-N bm25 hits
    top_bm_idx = sorted(range(len(bm25_norm)),
                        key=lambda i: bm25_norm[i],
                        reverse=True)[: len(sem_docs) or 8]

    bm_docs  = [docs_store[i]  for i in top_bm_idx]
    bm_metas = [metas_store[i] for i in top_bm_idx]
    bm_sims  = [bm25_norm[i]   for i in top_bm_idx]

    # --- 3) Merge by note_id with weighted score
    # seed with semantic
    combined = {}
    for d, m, s in zip(sem_docs, sem_metas, sem_sims):
        nid = m.get("note_id")
        combined[nid] = {
            "text": d,
            "created_at": m.get("created_at"),
            "sem": s,
            "bm25": 0.0,
        }

    # add bm25
    for d, m, s in zip(bm_docs, bm_metas, bm_sims):
        nid = m.get("note_id")
        if nid in combined:
            combined[nid]["bm25"] = max(combined[nid]["bm25"], s)
        else:
            combined[nid] = {
                "text": d,
                "created_at": m.get("created_at"),
                "sem": 0.0,
                "bm25": s,
            }

    # final score
    for v in combined.values():
        v["score"] = alpha * v["sem"] + (1 - alpha) * v["bm25"]

    ranked = sorted(combined.items(), key=lambda kv: kv[1]["score"], reverse=True)[:top_k]

    if not ranked or ranked[0][1]["score"] < min_confidence:
        return [], [], {
            "reason": "Low retrieval confidence",
            "best_score": ranked[0][1]["score"] if ranked else 0.0,
        }

    top_docs  = [v["text"] for _, v in ranked]
    top_metas = [{"note_id": k, "created_at": v["created_at"], "score": v["score"], "sem": v["sem"], "bm25": v["bm25"]}
                 for k, v in ranked]

    debug = {
        "alpha": alpha,
        "min_confidence": min_confidence,
        "semantic_hits": len(sem_docs),
        "bm25_considered": len(top_bm_idx),
        "top_scores": [m["score"] for m in top_metas],
    }
    return top_docs, top_metas, debug