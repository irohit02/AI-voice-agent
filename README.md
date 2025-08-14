# My AI Voice Agent Project

Yo! This is a voice agent I built. You can talk to it, and it talks back. It\'s powered by some cool AI APIs and a FastAPI backend.

## How it Works (The Gyaan)

It\'s pretty straightforward:
-   **Frontend**: Simple HTML/JS page where you can record your voice. No fancy frameworks, just plain old web stuff.
-   **Backend**: A FastAPI server that\'s the brains of the operation. It takes your audio, sends it to the right APIs, and gets a response.
-   **AI Magic**:
    -   **AssemblyAI**: Turns your speech into text.
    -   **Google Gemini**: Figures out what to say back.
    -   **Murf.ai**: Creates the AI\'s voice.

## Tech Stack

-   **Backend**: Python, FastAPI
-   **Frontend**: HTML, CSS, JavaScript
-   **APIs**: AssemblyAI, Google Gemini, Murf.ai
-   **Other Stuff**: `python-dotenv` for keys, `uvicorn` to run the server.

## Features (What it can do)

-   **Real-time Chat**: Talk to it and it replies instantly.
-   **Remembers Stuff**: It keeps track of the conversation, so you can ask follow-up questions.
-   **Decent Voice**: Uses Murf.ai so it doesn\'t sound like a robot from the 90s.
-   **Doesn\'t Crash Easily**: If an API is down, it has a fallback.

## How to Get this Thing Running

Follow these steps to run it on your machine.

### 1. Get the Code
```bash
git clone <repository_url>
cd voice-agent
```

### 2. Make a Virtual Environment
Do this so you don\'t mess up your global Python packages.
```bash
# For Mac/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\\venv\\Scripts\\activate
```

### 3. Install the Junk
This installs all the Python libraries it needs.
```bash
pip install -r requirements.txt
```

### 4. API Keys (Important!)
You need API keys for this to work.
1.  Create a file named `.env` in the main folder.
2.  Paste this inside and add your keys:

```
MURF_API_KEY=your_murf_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
GEMINI_API_KEY=your_gemini_api_key
```
Get these keys from their respective websites.

## Run It!

Finally, fire up the server.
```bash
uvicorn main:app --reload
```
Now go to `http://127.0.0.1:8000` in your browser. Have fun!

## API Stuff

-   `GET /`: The main page.
-   `POST /agent/chat/{session_id}`: The main endpoint. Handles the whole chat logic.
-   `POST /transcribe/file`: Just for turning speech to text.
-   `POST /generate-audio`: Just for turning text to speech.

## File Structure

```
.
├── .env              # Your API keys go here
├── main.py           # The main server code
├── README.md         # This file
├── requirements.txt  # All the python stuff to install
├── static/
│   └── script.js     # Frontend JS
├── templates/
│   └── index.html    # The webpage
└── uploads/
    └── ...           # For audio files
```

## About Errors
If something breaks (like an API is down), it won\'t just crash on you. It\'ll play a default audio message saying something\'s wrong.
