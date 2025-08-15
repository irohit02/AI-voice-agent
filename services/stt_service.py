import os
import assemblyai as aai
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

def transcribe_audio_file(file_path: str) -> str:
    print(f"Transcribing audio file: {file_path}")
    if not ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=500, detail={"stage": "stt", "message": "AssemblyAI API Key not found"})

    aai.settings.api_key = ASSEMBLYAI_API_KEY
    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(file_path)

    if transcript.error:
        raise HTTPException(status_code=500, detail={"stage": "stt", "message": transcript.error})

    print(f"Transcription: {transcript.text}")
    return transcript.text

