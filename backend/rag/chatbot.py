import chromadb
from sentence_transformers import SentenceTransformer
from langchain_ollama import ChatOllama
from langchain.memory import ConversationBufferMemory
from rag.vector_store import hybrid_retrieve  

# Initialize LLM and memory
llm = ChatOllama(model="llama3", temperature=0.1)
memory = ConversationBufferMemory(memory_key="chat_history")

# -------------------------------
# Full RAG workflow
# -------------------------------
def answer_query(query: str):
    """
    Full RAG workflow:
    1. Retrieve top notes using hybrid retriever (semantic + BM25)
    2. Build a contextual prompt
    3. Generate response from LLM (Ollama)
    4. Return the answer and sources
    """
    print(f"🗣️ Query received: {query}")

    # ✅ Step 1: Retrieve from Chroma + BM25
    top_docs, top_metas, debug_info = hybrid_retrieve(query, top_k=4)
    print(f"🔍 Hybrid retrieval debug: {debug_info}")
    if not top_docs:
        return {
            "answer": "I couldn’t find relevant information in the machine shop notes for that query.",
            "sources": [],
            "debug": debug_info,
        }

    print("\n🔍 Retrieved notes:")
    for m in top_metas:
        print(f"  - Note {m['note_id']} ({m['created_at']})")

    # ✅ Step 2: Build context
    context_text = "\n\n".join(
        [f"Note {m.get('note_id', '?')} ({m.get('created_at', 'N/A')}): {d}"
         for m, d in zip(top_metas, top_docs)]
    )

    # ✅ Step 3: Construct prompt
    prompt = f"""
You are a professional mechanical engineer and maintenance expert.
Use the following shop floor notes to answer the question precisely.
Reference the relevant note numbers and provide a practical, engineering-based answer.
If unsure, say so — do not make things up.

=== RELEVANT NOTES ===
{context_text}

=== QUESTION ===
{query}

Respond in a clear, StackOverflow-style answer with concise, factual reasoning.
"""

    # ✅ Step 4: Generate response from Ollama
    response = llm.invoke(prompt)

    # ✅ Step 5: Extract the message text safely
    if hasattr(response, "content"):
        response_text = response.content
    else:
        response_text = str(response)

    # ✅ Step 6: Save the exchange to memory
    try:
        memory.save_context({"input": query}, {"output": response_text})
    except Exception as e:
        print(f"⚠️ Skipped memory save due to: {e}")

    # ✅ Step 7: Return for frontend
    return {
        "answer": response_text,
        "sources": [
            {"note_id": m.get("note_id"), "created_at": m.get("created_at")}
            for m in top_metas
        ],
    }