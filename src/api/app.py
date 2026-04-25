from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.assistant.engine import assistant
from src.api.auth import validate_api_token
from src.config import settings
from src.memory.store import store
from src.observability.metrics import metrics
from src.scheduler.service import scheduler
from src.tools.catalog import call_tool
from src.voice.pipeline import voice_pipeline


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_title: str | None = None


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    details: str = ""
    priority: str = "medium"
    due_at: str | None = None


class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = ""
    category: str = "general"


class ReminderCreateRequest(BaseModel):
    message: str = Field(..., min_length=1)
    minutes: float = Field(..., gt=0)


class VoiceInputRequest(BaseModel):
    text: str = Field(..., min_length=1)


class VoiceFileRequest(BaseModel):
    audio_path: str = Field(..., min_length=1)
    provider: str | None = None


class VoiceSpeakRequest(BaseModel):
    text: str = Field(..., min_length=1)
    provider: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.rehydrate()
    store.log_event("startup", "info", "Public showcase assistant started")
    yield
    store.log_event("shutdown", "info", "Public showcase assistant stopped")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Public showcase AI assistant with safe automation, memory, and voice readiness.",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "core", "description": "Core health and dashboard endpoints."},
        {"name": "assistant", "description": "Chat and assistant orchestration."},
        {"name": "productivity", "description": "Tasks, notes, reminders, and facts."},
        {"name": "voice", "description": "Mock and optional real voice adapters."},
        {"name": "observability", "description": "Metrics, logs, and runtime diagnostics."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_timing_middleware(request: Request, call_next):
    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed_ms = (perf_counter() - started) * 1000
        metrics.record_request(request.url.path, status_code, elapsed_ms)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    store.log_event("unhandled_exception", "error", f"{request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if settings.frontend_enabled:
    static_dir = (Path(__file__).resolve().parent / "static")
    app.mount("/ui/static", StaticFiles(directory=str(static_dir)), name="ui-static")


@app.get("/ui", tags=["core"])
def dashboard_ui() -> FileResponse:
    static_dir = Path(__file__).resolve().parent / "static"
    return FileResponse(static_dir / "index.html")


@app.get("/", tags=["core"])
def root() -> dict[str, Any]:
    return {
        "name": settings.app_name,
        "status": "running",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "environment": settings.env,
    }


@app.get("/health", tags=["core"])
def health() -> dict[str, Any]:
    dashboard = assistant.dashboard()
    metrics_snapshot = metrics.snapshot()
    return {
        "status": "ok",
        "messages": len(dashboard["messages"]),
        "notes": len(dashboard["notes"]),
        "tasks": len(dashboard["tasks"]),
        "reminders": len(dashboard["reminders"]),
        "cpu_percent": metrics_snapshot["system"]["cpu_percent"],
        "memory_percent": metrics_snapshot["system"]["memory_percent"],
    }


@app.get("/dashboard", tags=["core"])
def dashboard(_: None = Depends(validate_api_token)) -> dict[str, Any]:
    return assistant.dashboard()


@app.post("/chat", tags=["assistant"])
def chat(request: ChatRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    return assistant.process_message(request.message, request.session_title)


@app.get("/tasks", tags=["productivity"])
def list_tasks(status: str | None = None, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    return {"tasks": store.list_tasks(status)}


@app.post("/tasks", tags=["productivity"])
def create_task(request: TaskCreateRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    task_id = store.add_task(request.title, request.details, request.priority, request.due_at)
    store.log_event("task_created", "info", request.title)
    metrics.record_tool_usage("create_task")
    return {"id": task_id, "title": request.title, "priority": request.priority}


@app.patch("/tasks/{task_id}/complete", tags=["productivity"])
def complete_task(task_id: int, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    if not store.complete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    store.log_event("task_completed", "info", f"Task #{task_id}")
    metrics.record_tool_usage("complete_task")
    return {"id": task_id, "status": "done"}


@app.get("/notes", tags=["productivity"])
def list_notes(category: str | None = None, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    return {"notes": store.list_notes(category)}


@app.post("/notes", tags=["productivity"])
def create_note(request: NoteCreateRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    note_id = store.add_note(request.title, request.content, request.category)
    store.log_event("note_created", "info", request.title)
    metrics.record_tool_usage("create_note")
    return {"id": note_id, "title": request.title, "category": request.category}


@app.get("/memory/facts", tags=["productivity"])
def list_facts(_: None = Depends(validate_api_token)) -> dict[str, Any]:
    return {"facts": store.list_facts()}


@app.post("/memory/facts", tags=["productivity"])
def set_fact(key: str, value: str, category: str = "general", _: None = Depends(validate_api_token)) -> dict[str, Any]:
    store.set_fact(key, value, category)
    store.log_event("fact_saved", "info", key)
    return {"key": key, "value": value, "category": category}


@app.get("/reminders", tags=["productivity"])
def list_reminders(_: None = Depends(validate_api_token)) -> dict[str, Any]:
    return {"reminders": store.list_reminders(), "active": scheduler.list_active()}


@app.post("/reminders", tags=["productivity"])
def create_reminder(request: ReminderCreateRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    reminder = scheduler.schedule(request.message, request.minutes)
    store.log_event("reminder_scheduled", "info", request.message)
    metrics.record_tool_usage("schedule_reminder")
    return reminder


@app.delete("/reminders/{reminder_id}", tags=["productivity"])
def cancel_reminder(reminder_id: int, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    if not scheduler.cancel(reminder_id):
        raise HTTPException(status_code=404, detail="Reminder not found")
    store.log_event("reminder_cancelled", "warning", f"Reminder #{reminder_id}")
    metrics.record_tool_usage("cancel_reminder")
    return {"id": reminder_id, "status": "cancelled"}


@app.get("/logs", tags=["observability"])
def logs(limit: int = 50, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    return {"events": store.list_events(limit)}


@app.get("/observability/summary", tags=["observability"])
def observability_summary(_: None = Depends(validate_api_token)) -> dict[str, Any]:
    events = store.list_events(100)
    error_events = [event for event in events if event.get("level") == "error"]
    return {
        "metrics": metrics.snapshot(),
        "recent_actions": events[:20],
        "recent_errors": error_events[:10],
    }


@app.get("/voice/capabilities", tags=["voice"])
def voice_capabilities(_: None = Depends(validate_api_token)) -> dict[str, Any]:
    return voice_pipeline.capabilities()


@app.post("/voice/mock/transcribe", tags=["voice"])
def voice_transcribe(request: VoiceInputRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    result = voice_pipeline.transcribe(request.text)
    return result.__dict__


@app.post("/voice/mock/speak", tags=["voice"])
def voice_speak(request: VoiceInputRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    result = voice_pipeline.speak(request.text)
    return result.__dict__


@app.post("/voice/transcribe", tags=["voice"])
def voice_transcribe_provider(request: VoiceFileRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    result = voice_pipeline.transcribe_audio_file(request.audio_path, request.provider)
    if not result.available:
        store.log_event("voice_error", "warning", result.message)
    return result.__dict__


@app.post("/voice/speak", tags=["voice"])
async def voice_speak_provider(request: VoiceSpeakRequest, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    result = await voice_pipeline.speak_with_provider(request.text, request.provider)
    if not result.available:
        store.log_event("voice_error", "warning", result.message)
    return result.__dict__


@app.post("/tools/{tool_name}", tags=["assistant"])
def run_tool(tool_name: str, payload: dict[str, Any] | None = None, _: None = Depends(validate_api_token)) -> dict[str, Any]:
    try:
        metrics.record_tool_usage(tool_name)
        return call_tool(tool_name, **(payload or {}))
    except Exception as exc:
        store.log_event("tool_error", "error", f"{tool_name}: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc
