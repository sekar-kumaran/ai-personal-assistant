from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Optional

from src.memory.store import store
from src.utils.logging import logger


@dataclass
class ScheduledReminder:
    id: int
    message: str
    due_at: datetime
    timer: threading.Timer | None = None


class ReminderScheduler:
    def __init__(self, on_fire: Optional[Callable[[str], None]] = None):
        self._lock = threading.RLock()
        self._reminders: dict[int, ScheduledReminder] = {}
        self._on_fire = on_fire

    def schedule(self, message: str, minutes: float) -> dict:
        minutes = max(0.1, float(minutes))
        due_at = datetime.now() + timedelta(minutes=minutes)
        reminder_id = store.add_reminder(message, due_at.isoformat())

        reminder = ScheduledReminder(reminder_id, message, due_at)

        timer = threading.Timer(minutes * 60, self._fire, args=(reminder_id,))
        timer.daemon = True
        reminder.timer = timer

        with self._lock:
            self._reminders[reminder_id] = reminder

        timer.start()
        logger.info("Scheduled reminder %s for %s", reminder_id, due_at.isoformat())
        return {
            "id": reminder_id,
            "message": message,
            "due_at": due_at.isoformat(),
            "status": "scheduled",
        }

    def rehydrate(self) -> None:
        now = datetime.now()
        for reminder in store.list_reminders():
            if reminder["status"] != "scheduled":
                continue
            due_at = datetime.fromisoformat(reminder["due_at"])
            if due_at <= now:
                store.mark_reminder_fired(int(reminder["id"]))
                continue
            remaining_seconds = max(1.0, (due_at - now).total_seconds())
            timer = threading.Timer(remaining_seconds, self._fire, args=(int(reminder["id"]),))
            timer.daemon = True
            with self._lock:
                self._reminders[int(reminder["id"])] = ScheduledReminder(
                    id=int(reminder["id"]),
                    message=reminder["message"],
                    due_at=due_at,
                    timer=timer,
                )
            timer.start()

    def list_active(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "id": reminder.id,
                    "message": reminder.message,
                    "due_at": reminder.due_at.isoformat(),
                    "seconds_remaining": max(0, round((reminder.due_at - datetime.now()).total_seconds())),
                }
                for reminder in self._reminders.values()
            ]

    def cancel(self, reminder_id: int) -> bool:
        with self._lock:
            reminder = self._reminders.pop(reminder_id, None)
        if reminder and reminder.timer:
            reminder.timer.cancel()
        return store.cancel_reminder(reminder_id)

    def _fire(self, reminder_id: int) -> None:
        with self._lock:
            reminder = self._reminders.pop(reminder_id, None)

        if reminder is None:
            return

        store.mark_reminder_fired(reminder_id)
        message = f"Reminder fired: {reminder.message}"
        logger.info(message)
        store.log_event("reminder_fired", "info", message)
        if self._on_fire:
            try:
                self._on_fire(reminder.message)
            except Exception as exc:
                logger.exception("Reminder callback failed: %s", exc)


scheduler = ReminderScheduler()
