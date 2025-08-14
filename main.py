from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import os
import requests
import shutil
import assemblyai as aai
import tempfile
import aiofiles
import google.generativeai as genai
from typing import Dict, List
from gtts import gTTS  # Day 11

# Load env vars
load_dotenv()

# FastAPI app setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev: allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# API Keys
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FALLBACK_AUDIO_URL = "/uploads/fallback_audio.mp3"

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# In-memory chat history store
chat_history: Dict[str, List[Dict[str, str]]] = {}

# Uploads folder
UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

# ----- MODELS -----
class TextInput(BaseModel):
    text: str
class LLMRequest(BaseModel):
    text: str

# ----- HELPERS -----
def _safe_requests_post(url: str, *, json: dict, headers: dict, timeout_seconds: int = 20):
    try:
        return requests.post(url, json=json, headers=headers, timeout=timeout_seconds)
    except requests.Timeout as exc:
        raise HTTPException(status_code=504, detail={"stage": "network", "message": f"Request to {url} timed out"}) from exc
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail={"stage": "network", "message": f"Request to {url} failed: {str(exc)}"}) from exc

def _generate_murf_audio_or_fail(text: str) -> str:
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail={"stage": "tts", "message": "Murf API Key not found"})

    murf_url = "https://api.murf.ai/v1/speech/generate"
    headers = {
        "accept": "application/json",
        "api-key": MURF_API_KEY,
        "Authorization": f"Bearer {MURF_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "voiceId": "en-US-natalie",
        "format": "mp3",
    }

    murf_response = _safe_requests_post(murf_url, json=payload, headers=headers)
    try:
        murf_response.raise_for_status()
    except requests.HTTPError as exc:
        try:
            err_json = murf_response.json()
        except Exception:
            err_json = {"message": murf_response.text or "Unknown Murf error"}
        raise HTTPException(status_code=502, detail={"stage": "tts", "message": "Murf request failed", "upstream": err_json}) from exc

    try:
        audio_url = murf_response.json().get("audioFile")
    except ValueError:
        audio_url = None

    if not audio_url:
        raise HTTPException(status_code=500, detail={"stage": "tts", "message": "No audio URL returned from Murf"})
    return audio_url

def _extract_gemini_text(llm_response) -> str:
    output_text = getattr(llm_response, "text", None)
    if not output_text and hasattr(llm_response, "candidates") and llm_response.candidates:
        parts = llm_response.candidates[0].content.parts
        if parts and hasattr(parts[0], "text"):
            output_text = parts[0].text
    return output_text or ""

# ----- GLOBAL EXCEPTION HANDLERS -----
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if not isinstance(detail, dict):
        detail = {"message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": detail})

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": {"message": "Internal server error"}},
    )

# ===== Day 11: Robust Error Handling & Fallback =====
FALLBACK_TEXT = "I'm having trouble connecting right now."
FALLBACK_AUDIO_FILE = Path("uploads/fallback_audio.mp3")

if not FALLBACK_AUDIO_FILE.exists():
    try:
        FALLBACK_AUDIO_FILE.parent.mkdir(parents=True, exist_ok=True)
        tts = gTTS(FALLBACK_TEXT)
        tts.save(FALLBACK_AUDIO_FILE)
        print(f"[ERROR] Generated fallback audio at {FALLBACK_AUDIO_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to generate fallback audio: {e}")

def _fallback_audio_response():
    return FileResponse(FALLBACK_AUDIO_FILE, media_type="audio/mpeg")

# ----- ROUTES -----
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate-audio")
def generate_audio(input: TextInput):
    try:
        if not input.text or not input.text.strip():
            raise HTTPException(status_code=400, detail={"stage": "input", "message": "Text is required"})
        audio_url = _generate_murf_audio_or_fail(input.text.strip())
        return {"ok": True, "audio_url": audio_url}
    except Exception as e:
        print(f"[ERROR] generate-audio failed: {e}")
        return _fallback_audio_response()

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    try:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        size_kb = round(Path(file_path).stat().st_size / 1024, 2)
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_kb": size_kb
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"stage": "upload", "message": f"Upload failed: {str(e)}"})

@app.post("/transcribe/file")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        if not ASSEMBLYAI_API_KEY:
            raise HTTPException(status_code=500, detail={"stage": "stt", "message": "AssemblyAI API Key not found"})
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_bytes = await file.read()
        temp_file.write(temp_bytes)
        temp_file.close()
        transcript = transcriber.transcribe(temp_file.name)
        os.remove(temp_file.name)
        return {"ok": True, "transcript": transcript.text}
    except Exception as e:
        print(f"[ERROR] STT failed: {e}")
        return _fallback_audio_response()

@app.post("/tts/echo")
async def echo_with_murf(file: UploadFile = File(...)):
    try:
        if not ASSEMBLYAI_API_KEY or not MURF_API_KEY:
            raise HTTPException(status_code=500, detail={"stage": "config", "message": "Missing API keys"})
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_bytes = await file.read()
        temp_file.write(temp_bytes)
        temp_file.close()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_file.name)
        os.remove(temp_file.name)
        audio_url = _generate_murf_audio_or_fail(transcript.text)
        return {"ok": True, "audio_url": audio_url, "transcript": transcript.text}
    except Exception as e:
        print(f"[ERROR] Echo TTS failed: {e}")
        return _fallback_audio_response()

@app.post("/llm/query")
async def llm_query(file: UploadFile = File(...)):
    try:
        if not GEMINI_API_KEY or not ASSEMBLYAI_API_KEY or not MURF_API_KEY:
            raise HTTPException(status_code=500, detail={"stage": "config", "message": "Missing one or more API keys"})
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_bytes = await file.read()
        temp_file.write(temp_bytes)
        temp_file.close()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_file.name)
        os.remove(temp_file.name) 
        user_text = transcript.text
        if not user_text:
            raise HTTPException(status_code=400, detail={"stage": "stt", "message": "No speech detected in audio"})
        model = genai.GenerativeModel("gemini-1.5-flash")
        llm_response = model.generate_content(user_text)
        output_text = _extract_gemini_text(llm_response)
        if not output_text:
            output_text = "No text returned from Gemini API."
        short_text = output_text[:3000]
        audio_url = _generate_murf_audio_or_fail(short_text)
        return {"ok": True, "transcript": user_text, "llm_response": output_text, "audio_url": audio_url}
    except Exception as e:
        print(f"[ERROR] LLM pipeline failed: {e}")
        return _fallback_audio_response()

@app.post("/agent/chat/{session_id}")
async def agent_chat(session_id: str, file: UploadFile = File(...)):
    try:
        if not GEMINI_API_KEY or not ASSEMBLYAI_API_KEY or not MURF_API_KEY:
            raise HTTPException(status_code=500, detail={"stage": "config", "message": "Missing one or more API keys"})
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_bytes = await file.read()
        temp_file.write(temp_bytes)
        temp_file.close()
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()
        transcript = transcriber.transcribe(temp_file.name)
        os.remove(temp_file.name)
        user_text = transcript.text.strip()
        if not user_text:
            raise HTTPException(status_code=400, detail={"stage": "stt", "message": "No speech detected in audio"})
        if session_id not in chat_history:
            chat_history[session_id] = []
        chat_history[session_id].append({"role": "user", "content": user_text})
        conversation_text = ""
        for msg in chat_history[session_id]:
            prefix = "User: " if msg["role"] == "user" else "Assistant: "
            conversation_text += prefix + msg["content"] + "\n"
        model = genai.GenerativeModel("gemini-1.5-flash")
        llm_response = model.generate_content(conversation_text)
        output_text = _extract_gemini_text(llm_response)
        if not output_text:
            output_text = "I couldn't generate a response."
        chat_history[session_id].append({"role": "assistant", "content": output_text})
        short_text = output_text[:3000]
        audio_url = _generate_murf_audio_or_fail(short_text)
        return {
            "ok": True,
            "session_id": session_id,
            "transcript": user_text,
            "llm_response": output_text,
            "audio_url": audio_url,
            "history": chat_history[session_id],
        }
    except Exception as e:
        print(f"[ERROR] Agent chat failed: {e}")
        return _fallback_audio_response()
