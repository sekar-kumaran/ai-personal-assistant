from __future__ import annotations

import importlib


def test_chat_routes_task_intent(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "showcase.db"))

    memory_store = importlib.import_module("src.memory.store")
    importlib.reload(memory_store)
    assistant_module = importlib.import_module("src.assistant.engine")
    importlib.reload(assistant_module)

    assistant = assistant_module.PublicAssistant()
    result = assistant.process_message("Add a task: prepare portfolio case studies")

    assert result["type"] == "tool_reply"
    assert "create_task" in result["tools_used"]
    assert "portfolio case studies" in result["content"].lower()


def test_reminder_intent(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWCASE_DB_PATH", str(tmp_path / "showcase.db"))

    memory_store = importlib.import_module("src.memory.store")
    importlib.reload(memory_store)
    scheduler_module = importlib.import_module("src.scheduler.service")
    importlib.reload(scheduler_module)
    tools_module = importlib.import_module("src.tools.catalog")
    importlib.reload(tools_module)
    assistant_module = importlib.import_module("src.assistant.engine")
    importlib.reload(assistant_module)

    assistant = assistant_module.PublicAssistant()
    result = assistant.process_message("Remind me in 5 minutes to review pull requests")

    assert result["type"] == "tool_reply"
    assert "schedule_reminder" in result["tools_used"]
