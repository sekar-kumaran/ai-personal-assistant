# AI Personal Assistant — Recommended (TL;DR)

One-line summary

- Production-style FastAPI assistant with intent routing, tool orchestration, lightweight memory (SQLite), optional voice adapters, and a Node.js integration client. Great demo for backend + AI orchestration roles.

Quick highlights (what to show recruiters)

- Run the API and open `/ui` to demo chat, tasks, reminders, and observability.
- Point out modular architecture: src/api, src/assistant, src/memory, src/scheduler, src/voice.
- Show the Node.js client calling the Python backend (node_client/).

Stack

- Language: Python 3.10+
- Frameworks: FastAPI, uvicorn
- Notable libs: pytest (tests), pydantic, sqlite (built-in), optional Ollama/LLM adapters

Minimal Quickstart (5 minutes)

```bash
# clone
git clone https://github.com/sekar-kumaran/ai-personal-assistant.git
cd ai-personal-assistant

# create virtualenv and install
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
pip install -r requirements.txt

# copy env and run (demo mode)
cp .env.example .env
python -m src.main serve
# Open: http://127.0.0.1:8001/ui and http://127.0.0.1:8001/docs
```

Quick demo CLI

```bash
python -m src.main demo "Create a task to prepare for interviews"
```

What I recommend adding (quick, high-impact)

- Add a short GIF or 1-minute demo video under assets/screenshots/ and link it in this README.
- Add a minimal LICENSE (MIT) so recruiters know how to reuse the code.
- Add badges (CI/tests) and a TL;DR at the top (this file serves as TL;DR).

Files I updated

- README_RECOMMENDED.md (this file) — short, recruiter-focused quickstart and highlights.

