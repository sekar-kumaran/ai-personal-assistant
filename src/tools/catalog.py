from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.memory.store import store
from src.scheduler.service import scheduler


@dataclass(frozen=True)
class Intent:
    tool_name: str
    args: dict[str, Any]


TOOL_DEFINITIONS = [
    {"name": "create_task", "description": "Create a productivity task."},
    {"name": "list_tasks", "description": "List active tasks."},
    {"name": "complete_task", "description": "Mark a task as done."},
    {"name": "create_note", "description": "Create a note."},
    {"name": "search_notes", "description": "Search notes."},
    {"name": "schedule_reminder", "description": "Schedule a reminder."},
    {"name": "list_reminders", "description": "List reminders."},
    {"name": "dashboard_summary", "description": "Summarize current assistant state."},
]


def tool_names() -> list[str]:
    return [item["name"] for item in TOOL_DEFINITIONS]


def detect_intent(message: str) -> Intent:
    text = message.strip().lower()

    reminder_match = re.search(r"remind me in (?P<minutes>\d+(?:\.\d+)?) minutes? to (?P<task>.+)", text)
    if reminder_match:
        return Intent(
            "schedule_reminder",
            {
                "message": reminder_match.group("task").strip(),
                "minutes": float(reminder_match.group("minutes")),
            },
        )

    task_match = re.search(r"(?:add|create) (?:a )?(?:task|todo)[:\s]+(?P<title>.+)", text)
    if task_match:
        return Intent("create_task", {"title": task_match.group("title").strip()})

    note_match = re.search(r"(?:note|remember)[:\s]+(?P<content>.+)", text)
    if note_match:
        return Intent(
            "create_note",
            {"title": note_match.group("content").strip()[:48], "content": note_match.group("content").strip()},
        )

    if any(keyword in text for keyword in ("show tasks", "list tasks", "my tasks")):
        return Intent("list_tasks", {})
    if any(keyword in text for keyword in ("show notes", "list notes", "my notes")):
        return Intent("search_notes", {"query": ""})
    if any(keyword in text for keyword in ("dashboard", "status summary", "overview")):
        return Intent("dashboard_summary", {})
    if any(keyword in text for keyword in ("show reminders", "list reminders", "my reminders")):
        return Intent("list_reminders", {})

    return Intent("chat", {})


def call_tool(tool_name: str, **kwargs: Any) -> dict[str, Any]:
    if tool_name == "create_task":
        task_id = store.add_task(kwargs["title"], kwargs.get("details", ""), kwargs.get("priority", "medium"), kwargs.get("due_at"))
        return {"tool": tool_name, "task_id": task_id, "title": kwargs["title"]}

    if tool_name == "list_tasks":
        return {"tool": tool_name, "tasks": store.list_tasks()}

    if tool_name == "complete_task":
        completed = store.complete_task(int(kwargs["task_id"]))
        return {"tool": tool_name, "completed": completed, "task_id": int(kwargs["task_id"])}

    if tool_name == "create_note":
        note_id = store.add_note(kwargs["title"], kwargs.get("content", ""), kwargs.get("category", "general"))
        return {"tool": tool_name, "note_id": note_id, "title": kwargs["title"]}

    if tool_name == "search_notes":
        query = kwargs.get("query", "")
        if query:
            notes = store.search_notes(query)
        else:
            notes = store.list_notes()
        return {"tool": tool_name, "notes": notes}

    if tool_name == "schedule_reminder":
        return {"tool": tool_name, "reminder": scheduler.schedule(kwargs["message"], kwargs["minutes"])}

    if tool_name == "list_reminders":
        return {"tool": tool_name, "reminders": store.list_reminders(), "active": scheduler.list_active()}

    if tool_name == "dashboard_summary":
        return {
            "tool": tool_name,
            "summary": {
                "notes": len(store.list_notes()),
                "tasks": len(store.list_tasks()),
                "reminders": len(store.list_reminders()),
                "facts": len(store.list_facts()),
            },
        }

    raise ValueError(f"Unknown tool: {tool_name}")


def format_tool_result(tool_result: dict[str, Any]) -> str:
    tool = tool_result.get("tool")
    if tool == "create_task":
        return f"Created task #{tool_result['task_id']}: {tool_result['title']}"
    if tool == "list_tasks":
        tasks = tool_result.get("tasks", [])
        if not tasks:
            return "You have no active tasks."
        return "Tasks: " + "; ".join(f"#{item['id']} {item['title']} [{item['status']}]" for item in tasks[:5])
    if tool == "complete_task":
        return "Task marked complete." if tool_result.get("completed") else "Task not found."
    if tool == "create_note":
        return f"Saved note #{tool_result['note_id']}: {tool_result['title']}"
    if tool == "search_notes":
        notes = tool_result.get("notes", [])
        if not notes:
            return "No matching notes found."
        return "Notes: " + "; ".join(f"#{item['id']} {item['title']}" for item in notes[:5])
    if tool == "schedule_reminder":
        reminder = tool_result["reminder"]
        return f"Reminder scheduled for {reminder['due_at']}: {reminder['message']}"
    if tool == "list_reminders":
        reminders = tool_result.get("reminders", [])
        if not reminders:
            return "No reminders saved yet."
        return "Reminders: " + "; ".join(f"#{item['id']} {item['message']} [{item['status']}]" for item in reminders[:5])
    if tool == "dashboard_summary":
        summary = tool_result.get("summary", {})
        return (
            f"Dashboard summary: {summary.get('tasks', 0)} tasks, {summary.get('notes', 0)} notes, "
            f"{summary.get('reminders', 0)} reminders, {summary.get('facts', 0)} facts."
        )
    return "Action completed."
