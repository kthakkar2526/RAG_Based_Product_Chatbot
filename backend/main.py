from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydub import AudioSegment
import speech_recognition as sr
import io
import time
import jwt
from datetime import datetime, timedelta
from typing import Optional
from rag.chatbot import answer_query as generate_answer
from rag.db import init_db, get_machines
import os
from pydantic import BaseModel

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Load credentials from environment variables
AUTH_USERS = {
    os.getenv("AUTH_USERNAME_1", "user1"): os.getenv("AUTH_PASSWORD_1", "pass1"),
    os.getenv("AUTH_USERNAME_2", "user2"): os.getenv("AUTH_PASSWORD_2", "pass2"),
    os.getenv("AUTH_USERNAME_3", "user3"): os.getenv("AUTH_PASSWORD_3", "pass3"),
    os.getenv("AUTH_USERNAME_4", "user4"): os.getenv("AUTH_PASSWORD_4", "pass4")
}
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "default-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """Initialize database tables on startup."""
    try:
        init_db()
        print("Database initialized on startup")
    except Exception as e:
        print(f"Warning: DB init on startup failed: {e}")

security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def create_access_token(username: str):
    """Generate JWT token for authenticated user."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    payload = {
        "sub": username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token from Authorization header."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in AUTH_USERS:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

@app.get("/")
def root():
    return {"status": "ok"}

@app.get("/api/machines/")
async def list_machines():
    """Return all machines for frontend dropdown."""
    machines = get_machines()
    return {"machines": machines}

@app.post("/api/login/", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    User login to obtain JWT token.
    """
    username = request.username
    password = request.password

    if username not in AUTH_USERS or AUTH_USERS[username] != password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    
    access_token = create_access_token(username=username)
    return LoginResponse(access_token=access_token)

@app.post("/api/transcribe/")
async def transcribe_audio(file: UploadFile = File(...),
                           current_user: str = Depends(verify_token)):
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
        
        print(f"🎧 Received: {file.filename} | Type: {content_type} | Size: {len(raw)} bytes | User: {current_user}")

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
async def chat_with_rag(query: str = Form(...),
                        machine_id: Optional[int] = Form(None),
                        current_user: str = Depends(verify_token)):
    """
    RAG chat - searches both worker notes and machine manuals.
    """
    print(f"User '{current_user}' asked: {query} (machine_id={machine_id})")
    result = generate_answer(query, machine_id=machine_id)
    return result

@app.post("/api/save_note/")
async def save_note(text: str = Form(...),
                    machine_id: Optional[int] = Form(None),
                    current_user: str = Depends(verify_token)):
    try:
        text = str(text).strip()

        if not text:
            raise HTTPException(status_code=400, detail="Note text cannot be empty")

        print(f"Saving note for user '{current_user}' (machine_id={machine_id})")

        from rag.vector_store import generate_embedding, load_bm25_index
        embedding = generate_embedding(text)

        from rag.db import save_note as db_save_note
        db_note_id = db_save_note(text, embedding, machine_id=machine_id)

        load_bm25_index(machine_id)

        print(f"Note saved with DB ID: {db_note_id}")
        return {"note_id": db_note_id, "message": "Note saved successfully"}

    except Exception as e:
        print(f"Error saving note: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error saving note: {str(e)}")
