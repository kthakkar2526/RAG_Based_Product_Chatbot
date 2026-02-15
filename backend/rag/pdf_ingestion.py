"""
PDF Ingestion Pipeline for machine manuals.

Extracts text, tables, and images from PDFs, chunks them with section awareness,
generates embeddings, and stores in the manual_chunks table.
"""

import os
import re
import io
import fitz  # PyMuPDF
from pathlib import Path


def extract_pages(pdf_path: str):
    """
    Extract text and images from each page of a PDF.
    Returns list of dicts: [{page_number, text, images: [bytes]}]
    """
    doc = fitz.open(pdf_path)
    pages = []

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Extract text with layout preservation
        text = page.get_text("text")

        # Extract images
        images = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                # Skip tiny images (icons, bullets, etc.)
                if pix.width < 100 or pix.height < 100:
                    pix = None
                    continue
                # Convert CMYK to RGB if needed
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_bytes = pix.tobytes("png")
                images.append(img_bytes)
                pix = None
            except Exception as e:
                print(f"  Warning: Could not extract image on page {page_num + 1}: {e}")

        pages.append({
            'page_number': page_num + 1,
            'text': text.strip(),
            'images': images,
        })

    doc.close()
    return pages


def detect_section_title(text: str):
    """Try to detect a section heading from the start of a text block."""
    lines = text.strip().split('\n')
    if not lines:
        return None

    first_line = lines[0].strip()
    # Heuristic: short uppercase line or numbered heading
    if len(first_line) < 100 and (
        first_line.isupper() or
        re.match(r'^\d+[\.\)]\s+', first_line) or
        re.match(r'^Chapter\s+\d+', first_line, re.IGNORECASE)
    ):
        return first_line
    return None


def chunk_text(text: str, page_number: int, max_tokens: int = 800, overlap_tokens: int = 200):
    """
    Split text into chunks respecting approximate token boundaries.
    Tries to break at paragraph/sentence boundaries.
    Returns list of dicts: [{text, page_number, section_title, chunk_type}]
    """
    if not text.strip():
        return []

    # Approximate tokens as words
    words = text.split()
    if len(words) <= max_tokens:
        return [{
            'text': text.strip(),
            'page_number': page_number,
            'section_title': detect_section_title(text),
            'chunk_type': 'text',
        }]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))

        # Try to break at a sentence boundary (period followed by space/newline)
        if end < len(words):
            chunk_text_str = ' '.join(words[start:end])
            # Look for last sentence break in the last 20% of the chunk
            search_start = int(len(chunk_text_str) * 0.8)
            last_period = chunk_text_str.rfind('. ', search_start)
            if last_period > 0:
                # Recalculate end based on the sentence break
                trimmed = chunk_text_str[:last_period + 1]
                end = start + len(trimmed.split())

        chunk_str = ' '.join(words[start:end]).strip()
        if chunk_str:
            chunks.append({
                'text': chunk_str,
                'page_number': page_number,
                'section_title': detect_section_title(chunk_str),
                'chunk_type': 'text',
            })

        start = end - overlap_tokens if end < len(words) else len(words)

    return chunks


def describe_image_with_gemini(image_bytes: bytes, api_key: str, page_number: int):
    """Use Gemini to generate a text description of an image."""
    try:
        import google.generativeai as genai
        from PIL import Image

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')

        img = Image.open(io.BytesIO(image_bytes))

        prompt = (
            "You are analyzing an image from a CNC machine or industrial equipment manual. "
            "Describe this image in detail for searchability. Include:\n"
            "- What the image shows (diagram, photo, screenshot, table, etc.)\n"
            "- All visible labels, part names, measurements, and annotations\n"
            "- The purpose or context of this image in a maintenance/operator manual\n"
            "- Any step numbers, warning symbols, or safety notes visible\n"
            "Be thorough but concise. This description will be used for text search."
        )

        response = model.generate_content([prompt, img])
        description = response.text.strip()
        return description

    except Exception as e:
        print(f"  Warning: Gemini image description failed for page {page_number}: {e}")
        return None


def process_pdf(pdf_path: str, manual_id: int, describe_images: bool = True):
    """
    Full pipeline: extract PDF -> chunk -> describe images -> embed -> store.

    Args:
        pdf_path: Path to the PDF file
        manual_id: The manual's DB id (must already exist in manuals table)
        describe_images: Whether to use Gemini for image descriptions

    Returns:
        Number of chunks created
    """
    from rag.vector_store import generate_embedding
    from rag.db import save_manual_chunk, delete_chunks_by_manual

    api_key = os.getenv("GEMINI_API_KEY") if describe_images else None
    if describe_images and not api_key:
        print("  Warning: GEMINI_API_KEY not set, skipping image descriptions")
        describe_images = False

    # Clear existing chunks for this manual (allows re-ingestion)
    delete_chunks_by_manual(manual_id)

    print(f"  Extracting pages from {pdf_path}...")
    pages = extract_pages(pdf_path)
    print(f"  Extracted {len(pages)} pages")

    total_chunks = 0

    for page in pages:
        page_num = page['page_number']

        # Chunk the text content
        text_chunks = chunk_text(page['text'], page_num)
        for chunk in text_chunks:
            if len(chunk['text'].split()) < 5:
                continue  # Skip very short chunks
            embedding = generate_embedding(chunk['text'])
            save_manual_chunk(
                manual_id=manual_id,
                chunk_text=chunk['text'],
                embedding=embedding,
                page_number=chunk['page_number'],
                section_title=chunk['section_title'],
                chunk_type=chunk['chunk_type'],
            )
            total_chunks += 1

        # Describe images and store as chunks
        if describe_images and page['images']:
            for i, img_bytes in enumerate(page['images']):
                description = describe_image_with_gemini(img_bytes, api_key, page_num)
                if description:
                    prefixed = f"[Image from page {page_num}]: {description}"
                    embedding = generate_embedding(prefixed)
                    save_manual_chunk(
                        manual_id=manual_id,
                        chunk_text=prefixed,
                        embedding=embedding,
                        page_number=page_num,
                        section_title=None,
                        chunk_type='image_description',
                    )
                    total_chunks += 1

        if page_num % 50 == 0:
            print(f"  Processed page {page_num}/{len(pages)}...")

    print(f"  Done: {total_chunks} chunks created for manual_id={manual_id}")
    return total_chunks
