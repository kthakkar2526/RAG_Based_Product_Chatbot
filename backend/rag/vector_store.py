import os, re
from datetime import datetime
from rank_bm25 import BM25Okapi
from pathlib import Path
import threading

# Lazy-load to avoid heavy import cost at container boot
_embedder = None
def get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        current_file = Path(__file__).resolve()
        backend_dir = current_file.parent.parent
        local_model_path = backend_dir / "models" / "all-MiniLM-L6-v2"

        if local_model_path.exists():
            print(f"Loading model from: {local_model_path}")
            _embedder = SentenceTransformer(str(local_model_path))
            print("Model loaded from local path")
        else:
            print("Local model not found, downloading from HuggingFace")
            _embedder = SentenceTransformer("all-MiniLM-L6-v2")

    return _embedder

def generate_embedding(text: str):
    """Generate embedding for the given text."""
    embedder = get_embedder()
    embedding = embedder.encode([text])[0].tolist()
    return embedding

_bm25_data = {'bm25': None, 'docs': [], 'metas': [], 'machine_id': None}
_bm25_lock = threading.Lock()

def load_bm25_index(machine_id: int = None):
    """Build BM25 index from notes + manual chunks, optionally filtered by machine."""
    global _bm25_data

    with _bm25_lock:
        try:
            from rag.db import get_all_notes_for_bm25, get_all_chunks_for_bm25

            notes = get_all_notes_for_bm25(machine_id)
            chunks = get_all_chunks_for_bm25(machine_id)

            docs = []
            metas = []

            # Add notes
            for note in notes:
                docs.append(note['text'])
                metas.append({
                    'source_type': 'note',
                    'note_id': str(note['id']),
                    'created_at': str(note['created_at']),
                })

            # Add manual chunks
            for chunk in chunks:
                docs.append(chunk['chunk_text'])
                metas.append({
                    'source_type': 'manual',
                    'chunk_id': str(chunk['id']),
                    'manual_title': chunk['manual_title'],
                    'page_number': chunk.get('page_number'),
                    'section_title': chunk.get('section_title'),
                    'chunk_type': chunk.get('chunk_type', 'text'),
                })

            if not docs:
                _bm25_data = {'bm25': BM25Okapi([[]]), 'docs': [], 'metas': [], 'machine_id': machine_id}
                print(f"BM25 index built with 0 documents (machine_id={machine_id})")
                return

            tokenized = [re.findall(r"\w+", doc.lower()) for doc in docs]
            _bm25_data = {
                'bm25': BM25Okapi(tokenized),
                'docs': docs,
                'metas': metas,
                'machine_id': machine_id,
            }

            print(f"BM25 index built: {len(notes)} notes + {len(chunks)} manual chunks (machine_id={machine_id})")
        except Exception as e:
            print(f"Error building BM25 index: {e}")
            _bm25_data = {'bm25': BM25Okapi([[]]), 'docs': [], 'metas': [], 'machine_id': machine_id}


def hybrid_retrieve(query: str, top_k: int = 5, alpha: float = 0.6, machine_id: int = None):
    """Retrieve documents using hybrid BM25 + vector similarity from both notes and manual chunks."""
    from rag.db import search_similar_notes, search_similar_chunks

    # Rebuild BM25 if machine changed or not initialized
    if _bm25_data['bm25'] is None or _bm25_data.get('machine_id') != machine_id:
        load_bm25_index(machine_id)

    query_embedding = generate_embedding(query)

    # Semantic search across both sources
    note_results = search_similar_notes(query_embedding, top_k=top_k * 2, machine_id=machine_id)
    chunk_results = search_similar_chunks(query_embedding, top_k=top_k * 2, machine_id=machine_id)

    # BM25 keyword search
    query_tokens = re.findall(r"\w+", query.lower())

    bm25_scores = []
    if _bm25_data['docs']:
        bm25_scores = _bm25_data['bm25'].get_scores(query_tokens)
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
        bm25_norm = [s / max_bm25 for s in bm25_scores]
    else:
        bm25_norm = []

    combined = {}

    # Add note semantic results
    for result in note_results:
        key = f"note_{result['id']}"
        combined[key] = {
            'text': result['text'],
            'source_type': 'note',
            'note_id': str(result['id']),
            'created_at': str(result['created_at']),
            'sem': float(result['similarity']),
            'bm25': 0.0,
        }

    # Add manual chunk semantic results
    for result in chunk_results:
        key = f"chunk_{result['id']}"
        combined[key] = {
            'text': result['chunk_text'],
            'source_type': 'manual',
            'manual_title': result['manual_title'],
            'page_number': result.get('page_number'),
            'section_title': result.get('section_title'),
            'chunk_type': result.get('chunk_type', 'text'),
            'sem': float(result['similarity']),
            'bm25': 0.0,
        }

    # Merge BM25 scores
    for idx, score in enumerate(bm25_norm):
        if idx >= len(_bm25_data['metas']):
            break
        meta = _bm25_data['metas'][idx]

        if meta['source_type'] == 'note':
            key = f"note_{meta['note_id']}"
        else:
            key = f"chunk_{meta['chunk_id']}"

        if key in combined:
            combined[key]['bm25'] = score
        else:
            entry = {
                'text': _bm25_data['docs'][idx],
                'source_type': meta['source_type'],
                'sem': 0.0,
                'bm25': score,
            }
            if meta['source_type'] == 'note':
                entry['note_id'] = meta['note_id']
                entry['created_at'] = meta['created_at']
            else:
                entry['manual_title'] = meta['manual_title']
                entry['page_number'] = meta.get('page_number')
                entry['section_title'] = meta.get('section_title')
                entry['chunk_type'] = meta.get('chunk_type', 'text')
            combined[key] = entry

    # Compute combined scores
    for v in combined.values():
        v['score'] = alpha * v['sem'] + (1 - alpha) * v['bm25']

    ranked = sorted(combined.items(), key=lambda kv: kv[1]['score'], reverse=True)[:top_k]

    if not ranked:
        return [], [], {"reason": "No documents available"}

    top_docs = [v['text'] for _, v in ranked]
    top_metas = [{'key': k, **v} for k, v in ranked]

    return top_docs, top_metas, {'top_scores': [m['score'] for m in top_metas]}
