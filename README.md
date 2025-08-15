# My AI Voice Agent Project

Yo! So, I built this voice agent. You can talk to it, and it talks back. It's a fun little project I put together using a FastAPI backend and a couple of sick AI APIs.

## How It Works (The Guts)

It's not rocket science. Here’s the breakdown:

*   **Frontend**: Just some plain old HTML and JavaScript. No fancy frameworks. You hit record, talk, and your voice gets shipped off to the backend.
*   **Backend**: This is a FastAPI server, the brains of the operation. It catches the audio, juggles a few API calls, and figures out what to send back.
*   **The AI Magic**:
    *   **AssemblyAI**: Takes your spoken words and turns them into text. Basically, speech-to-text.
    *   **Google Gemini**: The big brain. It decides what to say in reply.
    *   **Murf.ai**: Makes the AI voice sound less like a 90s robot and more like... well, a slightly better robot.

## Tech Stack (What It's Made Of)

*   **Backend**: Python, FastAPI
*   **Database**: SQLite with SQLAlchemy (so it actually remembers your chats now)
*   **Frontend**: HTML, CSS, JavaScript (the classic trio)
*   **APIs**: AssemblyAI, Google Gemini, Murf.ai
*   **Other Stuff**: `python-dotenv` for the secret keys, `uvicorn` to get the server running.

## Features (What It Can Actually Do)

*   **Real-time Chat**: You can have a pretty normal conversation with it.
*   **It Remembers!**: Thanks to the SQLite DB, it keeps track of your conversation history. No more amnesia after a refresh.
*   **Decent Voice**: The Murf.ai voice is pretty good.
*   **Doesn't Just Die**: If an API call fails or you send it silent audio, it has fallback responses instead of just crashing.

## How to Get This Thing Running

Follow these steps and you should be good to go.

### 1. Clone the Code

```bash
git clone <repository_url>
cd voice-agent
```

### 2. Make a Virtual Environment

Seriously, do this. Don't mess up your global Python packages.

```bash
# For Mac/Linux
python3 -m venv venv
source venv/bin/activate

# For Windows
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install the Junk

This installs all the Python libraries it needs to work.

```bash
pip install -r requirements.txt
```

### 4. API Keys (The Important Bit!)

This won't work without API keys.

1.  Create a file named `.env` in the main folder.
2.  Paste this inside and fill in your own keys. Get them from their websites.

```
MURF_API_KEY=your_murf_api_key
ASSEMBLYAI_API_KEY=your_assemblyai_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 5. Run It!

Time for the magic. Fire up the server.

```bash
uvicorn main:app --reload
```

The `--reload` flag is nice for development because the server restarts automatically when you change a file.

Now open your browser and go to `http://127.0.0.1:8000`. Have fun!

## API Stuff (Endpoints)

*   `GET /`: The main page.
*   `POST /agent/chat/{session_id}`: The main endpoint that does all the work.
*   `POST /transcribe/file`: Just for transcribing speech to text.
*   `POST /generate-audio`: Just for turning text to speech.

## File Structure (How It's Organized)

```
.
├── .env              # Your secret API keys live here
├── .gitignore        # Tells git what to ignore
├── chat_history.db   # The database file for conversations
├── database.py       # SQLAlchemy setup stuff
├── main.py           # The main FastAPI server code
├── models.py         # The database table schema
├── README.md         # You're reading it!
├── requirements.txt  # All the python libraries to install
├── schemas.py        # Pydantic models for request/response data
├── services/         # Logic for 3rd party APIs is separated out here
│   ├── llm_service.py
│   ├── stt_service.py
│   └── tts_service.py
├── static/
│   └── script.js     # The frontend JavaScript
├── templates/
│   └── index.html    # The main webpage
└── uploads/
    └── ...           # Where fallback audio files are stored
```
