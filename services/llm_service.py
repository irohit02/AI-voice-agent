
import os
import google.generativeai as genai
from fastapi import HTTPException
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_gemini_response(text: str) -> str:
    print("Getting response from Gemini...")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail={"stage": "llm", "message": "Gemini API Key not found"})

    model = genai.GenerativeModel("gemini-1.5-flash")
    llm_response = model.generate_content(text)
    output_text = _extract_gemini_text(llm_response)
    if not output_text:
        output_text = "No text returned from Gemini API. So I'm making this up."
    print(f"Gemini says: {output_text}")
    return output_text

def _extract_gemini_text(llm_response) -> str:
    print("Extracting text from Gemini response...")
    output_text = getattr(llm_response, "text", None)
    if not output_text and hasattr(llm_response, "candidates") and llm_response.candidates:
        parts = llm_response.candidates[0].content.parts
        if parts and hasattr(parts[0], "text"):
            output_text = parts[0].text
            print("Found text in Gemini candidates.")
    return output_text or ""

