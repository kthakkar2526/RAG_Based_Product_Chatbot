import os
from rag.vector_store import hybrid_retrieve


def answer_query(query: str, machine_id: int = None):
    print(f"Query received: {query} (machine_id={machine_id})")
    top_docs, top_metas, debug_info = hybrid_retrieve(query, top_k=5, machine_id=machine_id)
    print(f"Hybrid retrieval debug: {debug_info}")

    if not top_docs:
        return {"answer": "I couldn't find relevant information for that query.",
                "sources": [], "debug": debug_info}

    # Separate manual chunks and worker notes for the prompt
    manual_context_parts = []
    notes_context_parts = []
    sources = []

    for meta, doc in zip(top_metas, top_docs):
        if meta.get('source_type') == 'manual':
            page = meta.get('page_number', '?')
            title = meta.get('manual_title', 'Unknown Manual')
            section = meta.get('section_title', '')
            label = f"{title}, Page {page}"
            if section:
                label += f" ({section})"
            manual_context_parts.append(f"[{label}]: {doc}")
            sources.append({
                "source_type": "manual",
                "manual_title": title,
                "page_number": page,
                "section_title": section,
                "score": meta.get('score'),
            })
        else:
            note_id = meta.get('note_id', '?')
            created_at = meta.get('created_at', 'N/A')
            notes_context_parts.append(f"Note {note_id} ({created_at}): {doc}")
            sources.append({
                "source_type": "note",
                "note_id": note_id,
                "created_at": created_at,
                "score": meta.get('score'),
            })

    # Build prompt sections
    prompt_parts = [
        "You are a professional mechanical engineer and maintenance expert for a machine shop.",
        "You ONLY answer questions related to machines, their operation, maintenance, troubleshooting, and shop floor work.",
        "If the user asks anything unrelated to machines or shop operations (e.g. general knowledge, personal questions, coding, weather, etc.), "
        "politely decline and say: \"I'm your machine shop assistant. Please ask me questions related to your machines, their operation, maintenance, or troubleshooting.\"",
        "",
        "Use ALL of the following sources to answer the question. Every source provided is relevant — you MUST include information from EACH source in your answer.",
        "Be factual and cite your sources. If unsure, say so.",
    ]

    if manual_context_parts:
        prompt_parts.append("\n=== MACHINE MANUAL REFERENCES ===")
        prompt_parts.append("\n\n".join(manual_context_parts))

    if notes_context_parts:
        prompt_parts.append("\n=== WORKER NOTES ===")
        prompt_parts.append("\n\n".join(notes_context_parts))

    prompt_parts.append(f"\n=== QUESTION ===\n{query}")
    prompt_parts.append(
        "\nIMPORTANT RULES:\n"
        "1. You MUST reference and include information from EVERY source provided above — do not skip any source\n"
        "2. For manual content, reference the manual name and page number\n"
        "3. For worker notes, reference the note number and date\n"
        "4. If manual and worker notes conflict, mention both perspectives\n"
        "5. If the question is NOT about machines/maintenance/shop operations, politely refuse and ask the user to ask machine-related questions instead\n"
        "6. Structure your answer clearly so each source's contribution is visible"
    )

    prompt = "\n".join(prompt_parts)

    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        response_text = response.text
        print("LLM response generated")

        # If the LLM refused the question (not machine-related), don't return sources
        refusal_phrases = [
            "machine shop assistant",
            "please ask me questions related to",
            "please ask questions related to",
            "not related to machines",
            "can only help with machine",
        ]
        if any(phrase in response_text.lower() for phrase in refusal_phrases):
            sources = []

    except Exception as e:
        print(f"LLM error: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: return the raw context
        all_context = "\n\n".join(manual_context_parts + notes_context_parts)
        response_text = f"I found relevant information but couldn't generate a summary:\n\n{all_context}"

    return {"answer": response_text, "sources": sources, "debug": debug_info}
