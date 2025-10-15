from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import speech_recognition as sr
# from rag.generator import answer_query
import io
from rag.db import save_note_to_db
from datetime import datetime
from rag.vector_store import add_note_to_chroma
from rag.chatbot import answer_query
from fastapi import HTTPException
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()

# CORS (open in dev; restrict origins in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/api/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Accepts WebM (Chrome) or MP4/M4A (Safari) recordings and transcribes.
    """
    raw = await file.read()
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    # Detect format from filename or MIME
    file_ext = file.filename.split(".")[-1].lower()
    print(f"🎧 Received file: {file.filename}")

    audio = None
    try:
        if file_ext in ["webm", "ogg"]:
            audio = AudioSegment.from_file(io.BytesIO(raw), format="webm")
        elif file_ext in ["mp4", "m4a"]:
            audio = AudioSegment.from_file(io.BytesIO(raw), format="mp4")
        elif file_ext in ["mp3"]:
            audio = AudioSegment.from_file(io.BytesIO(raw), format="mp3")
        else:
            raise Exception(f"Unsupported format: {file_ext}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Audio decode failed: {str(e)}")

    # Convert to WAV (mono, 16kHz)
    wav_buf = io.BytesIO()
    audio.set_frame_rate(16000).set_channels(1).export(wav_buf, format="wav")
    wav_buf.seek(0)

    # Transcribe
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_buf) as source:
        audio_data = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        text = "(could not understand audio)"
    except sr.RequestError as e:
        text = f"(recognizer error: {e})"

    return {"text": text}

@app.post("/api/chat/")
async def chat_with_rag(query: str = Form(...)):
    """
    Conversational RAG using Ollama + LangChain with memory.
    Takes a user query, runs retrieval + generation,
    and returns both the answer and the notes used.x
    """
    from rag.chatbot import answer_query as generate_answer
    result = generate_answer(query)
    return result

@app.post("/api/save_note/")
async def save_note(note_id: int = Form(...), text: str = Form(...)):
    """
    Saves the note text to MySQL and ChromaDB.
    """
    try:
        # Save to SQL
        db_note_id = save_note_to_db(text)

        # Add to Chroma
        add_note_to_chroma(db_note_id, text)

        return {"status": "success", "note_id": db_note_id}
    except Exception as e:
        print("❌ Save Note Error:", e)
        return {"status": "error", "message": str(e)}