SYSTEM_PROMPT = """You are a public showcase productivity assistant.
Your job is to help with reminders, tasks, notes, and small planning workflows.
Be concise, practical, and transparent when a tool was used.
Never claim access to private production systems.
"""


def build_prompt(message: str, context_summary: str = "") -> str:
    parts = [SYSTEM_PROMPT.strip()]
    if context_summary:
        parts.append(f"Context: {context_summary.strip()}")
    parts.append(f"User request: {message.strip()}")
    parts.append("Respond with one short paragraph and mention any actions taken.")
    return "\n\n".join(parts)
