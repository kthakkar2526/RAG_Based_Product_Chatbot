from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydub import AudioSegment
import speech_recognition as sr
from rag.generator import answer_query
import io

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
    Accepts WebM (from frontend), converts to WAV in-memory, then transcribes.
    """
    raw = await file.read()

    # Decode WebM/Opus (browser default)
    audio = AudioSegment.from_file(io.BytesIO(raw), format="webm")

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
    Simple form-encoded endpoint for your RAG.
    """
    response = answer_query(query)
    return {"response": response}