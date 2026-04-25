from __future__ import annotations

import statistics
import threading
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import psutil


@dataclass
class ObservabilityMetrics:
    started_at: float = field(default_factory=time.time)
    total_requests: int = 0
    total_errors: int = 0
    request_by_path: Counter = field(default_factory=Counter)
    request_by_status: Counter = field(default_factory=Counter)
    latencies_ms: dict[str, deque] = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=300)))
    tool_usage: Counter = field(default_factory=Counter)
    assistant_response_ms: deque = field(default_factory=lambda: deque(maxlen=300))
    llm_provider_usage: Counter = field(default_factory=Counter)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def record_request(self, path: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.total_requests += 1
            if status_code >= 400:
                self.total_errors += 1
            self.request_by_path[path] += 1
            self.request_by_status[str(status_code)] += 1
            self.latencies_ms[path].append(duration_ms)

    def record_tool_usage(self, tool_name: str) -> None:
        with self._lock:
            self.tool_usage[tool_name] += 1

    def record_assistant_response(self, duration_ms: float, provider_name: str) -> None:
        with self._lock:
            self.assistant_response_ms.append(duration_ms)
            self.llm_provider_usage[provider_name] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            uptime_seconds = int(time.time() - self.started_at)
            latency_summary = {}
            for path, values in self.latencies_ms.items():
                if not values:
                    continue
                latency_summary[path] = {
                    "count": len(values),
                    "avg_ms": round(sum(values) / len(values), 2),
                    "p95_ms": round(_percentile(list(values), 95), 2),
                }

            assistant_avg = round(statistics.mean(self.assistant_response_ms), 2) if self.assistant_response_ms else 0.0
            assistant_p95 = round(_percentile(list(self.assistant_response_ms), 95), 2) if self.assistant_response_ms else 0.0

            return {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "uptime_seconds": uptime_seconds,
                "requests": {
                    "total": self.total_requests,
                    "errors": self.total_errors,
                    "by_path": dict(self.request_by_path),
                    "by_status": dict(self.request_by_status),
                    "latency": latency_summary,
                },
                "assistant": {
                    "avg_response_ms": assistant_avg,
                    "p95_response_ms": assistant_p95,
                    "llm_provider_usage": dict(self.llm_provider_usage),
                },
                "tools": {
                    "usage_count": dict(self.tool_usage),
                    "top": self.tool_usage.most_common(10),
                },
                "system": _system_health(),
            }


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    idx = max(0, min(len(values) - 1, int(round((percentile / 100) * (len(values) - 1)))))
    return float(values[idx])


def _system_health() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.0)
    return {
        "cpu_percent": cpu,
        "memory_percent": vm.percent,
        "memory_available_mb": round(vm.available / (1024 * 1024), 1),
        "process_count": len(psutil.pids()),
    }


metrics = ObservabilityMetrics()
