from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import speech_recognition as sr
import io
from rag.db import save_note_to_db
from datetime import datetime
from rag.vector_store import add_note_to_chroma
from rag.chatbot import answer_query
from fastapi import HTTPException
import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

app = FastAPI()

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
    Accepts WebM (Chrome/Firefox), MP4 (Safari), or MP3 recordings and transcribes.
    """
    try:
        raw = await file.read()
        if len(raw) == 0:
            raise HTTPException(status_code=400, detail="Empty audio file received")

        # Detect format from content-type and filename
        content_type = file.content_type or ""
        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        
        print(f"🎧 Received: {file.filename} | Type: {content_type} | Size: {len(raw)} bytes")

        # Try to load audio based on format
        audio = None
        formats_to_try = []
        
        # Determine which formats to attempt
        if "webm" in content_type or file_ext == "webm":
            formats_to_try = ["webm", "ogg"]
        elif "mp4" in content_type or file_ext in ["mp4", "m4a"]:
            formats_to_try = ["mp4", "m4a"]
        elif "mpeg" in content_type or file_ext == "mp3":
            formats_to_try = ["mp3"]
        else:
            # Try common formats as fallback
            formats_to_try = ["webm", "mp4", "mp3", "ogg"]

        # Attempt to decode audio
        last_error = None
        for fmt in formats_to_try:
            try:
                audio = AudioSegment.from_file(io.BytesIO(raw), format=fmt)
                print(f"✅ Successfully decoded as {fmt}")
                break
            except Exception as e:
                last_error = e
                print(f"⚠️ Failed to decode as {fmt}: {e}")
                continue

        if audio is None:
            raise HTTPException(
                status_code=400, 
                detail=f"Could not decode audio. Tried formats: {formats_to_try}. Last error: {str(last_error)}"
            )

        # Check if audio has content
        if len(audio) < 100:  # Less than 100ms
            raise HTTPException(status_code=400, detail="Audio too short (less than 100ms)")

        # Convert to WAV for speech recognition (16kHz, mono)
        wav_buf = io.BytesIO()
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_buf, format="wav")
        wav_buf.seek(0)
        
        print(f"🔊 Audio duration: {len(audio)}ms, Frame rate: {audio.frame_rate}Hz")

        # Transcribe using Google Speech Recognition
        recognizer = sr.Recognizer()
        
        # Adjust for ambient noise and energy threshold
        with sr.AudioFile(wav_buf) as source:
            # Adjust for background noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)

        try:
            print("🎤 Attempting transcription...")
            text = recognizer.recognize_google(audio_data, language="en-US")
            print(f"✅ Transcribed: {text}")
            return {"text": text}
            
        except sr.UnknownValueError:
            print("⚠️ Could not understand audio")
            return {"text": "", "error": "Could not understand audio. Please speak clearly and try again."}
            
        except sr.RequestError as e:
            print(f"❌ API Error: {e}")
            raise HTTPException(
                status_code=503, 
                detail=f"Speech recognition service error: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@app.post("/api/chat/")
async def chat_with_rag(query: str = Form(...)):
    """
    Conversational RAG using Ollama + LangChain with memory.
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
        db_note_id = save_note_to_db(text)
        add_note_to_chroma(db_note_id, text)
        return {"status": "success", "note_id": db_note_id}
    except Exception as e:
        print("❌ Save Note Error:", e)
        raise HTTPException(status_code=500, detail=str(e))