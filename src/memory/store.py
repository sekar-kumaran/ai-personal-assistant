from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.config import settings
from src.utils.logging import logger


class ShowcaseStore:
    # Usage: initialize the store with a SQLite file path and auto-create schema.
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    # Usage: open a thread-safe DB connection that auto-commits or rolls back.
    @contextmanager
    def connection(self):
        with self._lock:
            conn = sqlite3.connect(str(self.db_path), timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    # Usage: create all required tables before handling any app requests.
    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'pending',
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'scheduled',
                    created_at TEXT NOT NULL,
                    fired_at TEXT
                );

                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    # Usage: start a new active session and deactivate any previously active session.
    def create_session(self, title: str) -> int:
        with self.connection() as conn:
            conn.execute("UPDATE sessions SET is_active = 0 WHERE is_active = 1")
            cursor = conn.execute(
                "INSERT INTO sessions (title, created_at, is_active) VALUES (?, ?, 1)",
                (title, datetime.now().isoformat(timespec="seconds")),
            )
            return int(cursor.lastrowid)

    # Usage: fetch the current active session id, creating one when missing.
    def get_active_session_id(self) -> int:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row:
                return int(row[0])
        return self.create_session("Showcase session")

    # Usage: persist a chat message row for the active session.
    def add_message(self, role: str, content: str, metadata: Optional[dict[str, Any]] = None) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    self.get_active_session_id(),
                    role,
                    content,
                    json.dumps(metadata) if metadata else None,
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )

    # Usage: read recent chat messages for the active session in chronological order.
    def list_messages(self, limit: int = 20) -> list[dict[str, Any]]:
        session_id = self.get_active_session_id()
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT role, content, metadata, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        items = [dict(row) for row in rows]
        return list(reversed(items))

    # Usage: create a persistent note with title/content/category metadata.
    def add_note(self, title: str, content: str, category: str = "general") -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO notes (title, content, category, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (title, content, category, now, now),
            )
            return int(cursor.lastrowid)

    # Usage: list non-deleted notes, optionally filtered by category.
    def list_notes(self, category: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM notes WHERE is_deleted = 0"
        params: list[Any] = []
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY updated_at DESC"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    # Usage: search note titles and content using a keyword query.
    def search_notes(self, query: str) -> list[dict[str, Any]]:
        wildcard = f"%{query}%"
        with self.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM notes
                WHERE is_deleted = 0 AND (title LIKE ? OR content LIKE ?)
                ORDER BY updated_at DESC
                """,
                (wildcard, wildcard),
            ).fetchall()
        return [dict(row) for row in rows]

    # Usage: create a task with priority, optional details, and optional due date.
    def add_task(self, title: str, details: str = "", priority: str = "medium", due_at: str | None = None) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (title, details, priority, due_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (title, details, priority, due_at, now, now),
            )
            return int(cursor.lastrowid)

    # Usage: list active tasks and optionally filter by task status.
    def list_tasks(self, status: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE is_deleted = 0"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY CASE priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, created_at DESC"
        with self.connection() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    # Usage: mark a task as done and update its last-modified timestamp.
    def complete_task(self, task_id: int) -> bool:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connection() as conn:
            cursor = conn.execute(
                "UPDATE tasks SET status = 'done', updated_at = ? WHERE id = ? AND is_deleted = 0",
                (now, task_id),
            )
            return cursor.rowcount > 0

    # Usage: save a scheduled reminder record before timer execution.
    def add_reminder(self, message: str, due_at: str) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO reminders (message, due_at, status, created_at) VALUES (?, ?, 'scheduled', ?)",
                (message, due_at, now),
            )
            return int(cursor.lastrowid)

    # Usage: fetch reminder history with current statuses.
    def list_reminders(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM reminders ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    # Usage: cancel a pending reminder by id if it has not fired yet.
    def cancel_reminder(self, reminder_id: int) -> bool:
        with self.connection() as conn:
            cursor = conn.execute(
                "UPDATE reminders SET status = 'cancelled' WHERE id = ? AND status = 'scheduled'",
                (reminder_id,),
            )
            return cursor.rowcount > 0

    # Usage: mark a reminder as fired when its timer callback runs.
    def mark_reminder_fired(self, reminder_id: int) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE reminders SET status = 'fired', fired_at = ? WHERE id = ?",
                (datetime.now().isoformat(timespec="seconds"), reminder_id),
            )

    # Usage: store or update a key-value fact for lightweight assistant memory.
    def set_fact(self, key: str, value: str, category: str = "general") -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO facts (key, value, category, updated_at) VALUES (?, ?, ?, ?)",
                (key, value, category, datetime.now().isoformat(timespec="seconds")),
            )

    # Usage: retrieve all saved facts ordered by category and key.
    def list_facts(self) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM facts ORDER BY category, key").fetchall()
        return [dict(row) for row in rows]

    # Usage: append an event entry for audit and observability timelines.
    def log_event(self, event_type: str, level: str, details: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO audit_events (event_type, level, details, created_at) VALUES (?, ?, ?, ?)",
                (event_type, level, details, datetime.now().isoformat(timespec="seconds")),
            )

    # Usage: fetch recent audit events for logs and dashboard views.
    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


store = ShowcaseStore(settings.db_path)
