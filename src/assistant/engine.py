from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from src.assistant.llm import get_llm_client
from src.config import settings
from src.assistant.prompts import SYSTEM_PROMPT, build_prompt
from src.memory.store import store
from src.observability.metrics import metrics
from src.tools.catalog import call_tool, detect_intent, format_tool_result
from src.utils.logging import logger


@dataclass
class AssistantResponse:
    type: str
    content: str
    tools_used: list[str]
    metadata: dict[str, Any]


class PublicAssistant:
    def __init__(self):
        self.llm = get_llm_client()

    def process_message(self, message: str, session_title: str | None = None) -> dict[str, Any]:
        started = perf_counter()
        if session_title:
            store.create_session(session_title)

        intent = detect_intent(message)
        store.add_message("user", message, {"intent": intent.tool_name})
        store.log_event("chat_received", "info", message)

        tools_used: list[str] = []
        metadata: dict[str, Any] = {"intent": intent.tool_name}

        if intent.tool_name != "chat":
            tool_result = call_tool(intent.tool_name, **intent.args)
            tools_used.append(intent.tool_name)
            metrics.record_tool_usage(intent.tool_name)
            store.log_event("tool_used", "info", intent.tool_name)
            metadata["tool_result"] = tool_result
            prompt = build_prompt(message, format_tool_result(tool_result))
            content = self.llm.generate(SYSTEM_PROMPT, prompt)
            content = f"{content}\n\n{format_tool_result(tool_result)}"
            response_type = "tool_reply"
        else:
            prompt = build_prompt(message, "No tool required. Provide a concise assistant reply.")
            content = self.llm.generate(SYSTEM_PROMPT, prompt)
            response_type = "chat_reply"

        payload = {
            "type": response_type,
            "content": content,
            "tools_used": tools_used,
            "metadata": metadata,
        }

        store.add_message("assistant", content, metadata)
        metrics.record_assistant_response((perf_counter() - started) * 1000, settings.llm_provider)
        logger.info("Assistant response generated with type=%s", response_type)
        return payload

    def dashboard(self) -> dict[str, Any]:
        return {
            "messages": store.list_messages(),
            "notes": store.list_notes(),
            "tasks": store.list_tasks(),
            "reminders": store.list_reminders(),
            "facts": store.list_facts(),
            "events": store.list_events(),
        }


assistant = PublicAssistant()
