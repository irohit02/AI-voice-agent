from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
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
import aiofiles  # <--- for async file write

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

# Uploads folder
UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)


# ----- MODELS -----
class TextInput(BaseModel):
    text: str


# ----- ROUTES -----

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate-audio")
def generate_audio(input: TextInput):
    if not MURF_API_KEY:
        raise HTTPException(status_code=500, detail="Murf API Key not found")

    try:
        url = "https://api.murf.ai/v1/speech/generate"
        headers = {
            "accept": "application/json",
            "api-key": MURF_API_KEY,
            "Authorization": f"Bearer {MURF_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "text": input.text,
            "voiceId": "en-US-natalie",
            "format": "mp3"
        }

        response = requests.post(url, json=payload, headers=headers)
        print("Murf response:", response.text)
        response.raise_for_status()

        audio_url = response.json().get("audioFile")
        if not audio_url:
            raise HTTPException(status_code=500, detail="No audio URL returned from Murf")

        return {"audio_url": audio_url}

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Murf request failed: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/transcribe/file")
async def transcribe_audio(file: UploadFile = File(...)):
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail="AssemblyAI API Key not found")

    try:
        aai.settings.api_key = ASSEMBLYAI_API_KEY
        transcriber = aai.Transcriber()

        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_bytes = await file.read()
        temp_file.write(temp_bytes)
        temp_file.close()

        # Transcribe from file path
        transcript = transcriber.transcribe(temp_file.name)

        os.remove(temp_file.name)

        return {
            "transcript": transcript.text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
