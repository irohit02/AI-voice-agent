# IT'S ALIIIIIVE! (hopefully)
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from pathlib import Path
import os
import tempfile
import aiofiles
from typing import Dict, List
from gtts import gTTS
import logging

from schemas import (
    TextInput,
    AudioGenerationResponse,
    UploadResponse,
    TranscriptionResponse,
    EchoResponse,
    LLMResponse,
    ChatResponse,
)
from services.tts_service import generate_murf_audio
from services.stt_service import transcribe_audio_file
from services.llm_service import get_gemini_response

import logging
from fastapi import Depends
from sqlalchemy.orm import Session

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- VARS & CONFIG ---

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FASTAPI SETUP ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# --- GLOBAL EXCEPTION HANDLERS ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if not isinstance(detail, dict):
        detail = {"message": str(detail)}
    logger.error(f"HTTP Exception: {exc.status_code} - {detail}")
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": {"message": "Internal server error"}},
    )

# --- FALLBACK AUDIO ---
FALLBACK_TEXT = "I'm having trouble connecting right now."
FALLBACK_AUDIO_FILE = Path(f"{UPLOAD_FOLDER}/fallback_audio.mp3")
NO_SPEECH_TEXT = "I'm sorry, I couldn't hear you. Please try again."
NO_SPEECH_AUDIO_FILE = Path(f"{UPLOAD_FOLDER}/no_speech_audio.mp3")

if not FALLBACK_AUDIO_FILE.exists():
    try:
        logger.info("Fallback audio not found. Generating a new one.")
        FALLBACK_AUDIO_FILE.parent.mkdir(parents=True, exist_ok=True)
        tts = gTTS(FALLBACK_TEXT)
        tts.save(FALLBACK_AUDIO_FILE)
        logger.info(f"Generated fallback audio at {FALLBACK_AUDIO_FILE}")
    except Exception as e:
        logger.error(f"Failed to generate fallback audio: {e}")

if not NO_SPEECH_AUDIO_FILE.exists():
    try:
        logger.info("No speech fallback audio not found. Generating a new one.")
        NO_SPEECH_AUDIO_FILE.parent.mkdir(parents=True, exist_ok=True)
        tts = gTTS(NO_SPEECH_TEXT)
        tts.save(NO_SPEECH_AUDIO_FILE)
        logger.info(f"Generated no speech fallback audio at {NO_SPEECH_AUDIO_FILE}")
    except Exception as e:
        logger.error(f"Failed to generate no speech fallback audio: {e}")

def _fallback_audio_response():
    logger.warning("Serving up the fallback audio.")
    return FileResponse(FALLBACK_AUDIO_FILE, media_type="audio/mpeg")

def _no_speech_detected_response():
    logger.warning("No speech detected. Serving up the specific fallback audio.")
    return FileResponse(NO_SPEECH_AUDIO_FILE, media_type="audio/mpeg")


# --- API ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    logger.info("Serving up the homepage.")
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-audio", response_model=AudioGenerationResponse)
def generate_audio_endpoint(input: TextInput):
    try:
        logger.info(f"Generating audio for text: {input.text}")
        if not input.text or not input.text.strip():
            raise HTTPException(status_code=400, detail={"stage": "input", "message": "Text is required"})
        audio_url = generate_murf_audio(input.text.strip())
        return {"ok": True, "audio_url": audio_url}
    except Exception as e:
        logger.error(f"generate-audio failed: {e}")
        return _fallback_audio_response()

@app.post("/upload-audio", response_model=UploadResponse)
async def upload_audio(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        logger.info(f"Uploading file: {file.filename} to {file_path}")
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        size_kb = round(Path(file_path).stat().st_size / 1024, 2)
        logger.info(f"File uploaded successfully. Size: {size_kb} KB")
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_kb": size_kb
        }
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail={"stage": "upload", "message": f"Upload failed: {str(e)}"})

@app.post("/transcribe/file", response_model=TranscriptionResponse)
async def transcribe_audio_endpoint(file: UploadFile = File(...)):
    try:
        logger.info(f"Transcribing audio file: {file.filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_bytes = await file.read()
            temp_file.write(temp_bytes)
            temp_file_path = temp_file.name
        
        transcript_text = transcribe_audio_file(temp_file_path)
        os.remove(temp_file_path)
        
        return {"ok": True, "transcript": transcript_text}
    except Exception as e:
        logger.error(f"STT failed: {e}")
        return _fallback_audio_response()

@app.post("/tts/echo", response_model=EchoResponse)
async def echo_with_murf(file: UploadFile = File(...)):
    try:
        logger.info(f"Echoing audio file: {file.filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_bytes = await file.read()
            temp_file.write(temp_bytes)
            temp_file_path = temp_file.name
        
        transcript_text = transcribe_audio_file(temp_file_path)
        os.remove(temp_file_path)
        
        logger.info(f"Echoing back: {transcript_text}")
        audio_url = generate_murf_audio(transcript_text)
        return {"ok": True, "audio_url": audio_url, "transcript": transcript_text}
    except Exception as e:
        logger.error(f"Echo TTS failed: {e}")
        return _fallback_audio_response()

@app.post("/llm/query", response_model=LLMResponse)
async def llm_query(file: UploadFile = File(...)):
    try:
        logger.info(f"Running the full LLM query pipeline for file: {file.filename}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_bytes = await file.read()
            temp_file.write(temp_bytes)
            temp_file_path = temp_file.name
            
        user_text = transcribe_audio_file(temp_file_path)
        os.remove(temp_file_path)

        if not user_text:
            return _no_speech_detected_response()
        
        logger.info(f"User said: {user_text}")

        output_text = get_gemini_response(user_text)
        
        short_text = output_text[:3000] # Murf has a character limit
        audio_url = generate_murf_audio(short_text)
        return {"ok": True, "transcript": user_text, "llm_response": output_text, "audio_url": audio_url}
    except Exception as e:
        logger.error(f"LLM pipeline failed: {e}")
        return _fallback_audio_response()

# --- DATABASE CHAT ---

@app.post("/agent/chat/{session_id}", response_model=ChatResponse)
async def agent_chat(session_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        logger.info(f"Agent chat for session: {session_id}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_bytes = await file.read()
            temp_file.write(temp_bytes)
            temp_file_path = temp_file.name
            
        user_text = transcribe_audio_file(temp_file_path).strip()
        os.remove(temp_file_path)

        if not user_text:
            return _no_speech_detected_response()

        db_history = db.query(models.ChatHistory).filter(models.ChatHistory.session_id == session_id).all()
        
        conversation_text = ""
        for msg in db_history:
            prefix = "User: " if msg.role == "user" else "Assistant: "
            conversation_text += prefix + msg.content + "\n"
            
        conversation_text += "User: " + user_text + "\n"
            
        logger.info(f"Sending this to Gemini: {conversation_text}")

        output_text = get_gemini_response(conversation_text)

        db.add(models.ChatHistory(session_id=session_id, role="user", content=user_text))
        db.add(models.ChatHistory(session_id=session_id, role="assistant", content=output_text))
        db.commit()

        logger.info(f"Gemini responded with: {output_text}")

        short_text = output_text[:3000]
        audio_url = generate_murf_audio(short_text)

        updated_history = db.query(models.ChatHistory).filter(models.ChatHistory.session_id == session_id).all()

        return {
            "ok": True,
            "session_id": session_id,
            "transcript": user_text,
            "llm_response": output_text,
            "audio_url": audio_url,
            "history": [{"role": msg.role, "content": msg.content} for msg in updated_history],
        }
    except Exception as e:
        logger.error(f"Agent chat failed: {e}")
        return _fallback_audio_response()
