
import os
import requests
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

MURF_API_KEY = os.getenv("MURF_API_KEY")

def _safe_requests_post(url: str, *, json: dict, headers: dict, timeout_seconds: int = 20):
    try:
        print(f"Making a POST request to: {url}")
        return requests.post(url, json=json, headers=headers, timeout=timeout_seconds)
    except requests.Timeout as exc:
        print(f"Request to {url} timed out. Bummer.")
        raise HTTPException(status_code=504, detail={"stage": "network", "message": f"Request to {url} timed out"}) from exc
    except requests.RequestException as exc:
        print(f"Request to {url} failed. Double bummer.")
        raise HTTPException(status_code=502, detail={"stage": "network", "message": f"Request to {url} failed: {str(exc)}"}) from exc

def generate_murf_audio(text: str) -> str:
    print(f"Generating Murf audio for text: {text[:30]}...")
    if not MURF_API_KEY:
        print("Murf API Key not found. Can't make the robot talk.")
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
        print(f"Murf request failed. Status code: {murf_response.status_code}")
        try:
            err_json = murf_response.json()
            print(f"Murf error: {err_json}")
        except Exception:
            err_json = {"message": murf_response.text or "Unknown Murf error"}
        raise HTTPException(status_code=502, detail={"stage": "tts", "message": "Murf request failed", "upstream": err_json}) from exc

    try:
        audio_url = murf_response.json().get("audioFile")
        print(f"Got audio URL from Murf: {audio_url}")
    except ValueError:
        audio_url = None

    if not audio_url:
        print("No audio URL from Murf. Something is very wrong.")
        raise HTTPException(status_code=500, detail={"stage": "tts", "message": "No audio URL returned from Murf"})
    return audio_url

