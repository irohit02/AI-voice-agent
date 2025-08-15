from pydantic import BaseModel
from typing import List, Dict

class TextInput(BaseModel):
    text: str

class AudioGenerationResponse(BaseModel):
    ok: bool
    audio_url: str

class UploadResponse(BaseModel):
    filename: str
    content_type: str
    size_kb: float

class TranscriptionResponse(BaseModel):
    ok: bool
    transcript: str

class EchoResponse(BaseModel):
    ok: bool
    audio_url: str
    transcript: str

class LLMResponse(BaseModel):
    ok: bool
    transcript: str
    llm_response: str
    audio_url: str

class ChatResponse(BaseModel):
    ok: bool
    session_id: str
    transcript: str
    llm_response: str
    audio_url: str
    history: List[Dict[str, str]]

