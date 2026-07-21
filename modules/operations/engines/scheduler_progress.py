"""Append-only scheduler collection progress log."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class SchedulerProgressLog:
    """Fixed-step progress events for scheduler collection runs."""

    def __init__(self, run_id: str, *, on_update=None):
        self.run_id = run_id
        self.events: list[dict[str, Any]] = []
        self._active_step = ""
        self._on_update = on_update

    def _ts(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def append(self, step: str, status: str, *, detail: str = "") -> dict[str, Any]:
        status_norm = str(status or "Completed").strip()
        if status_norm.lower() == "running":
            self._active_step = step
        elif step == self._active_step and status_norm.lower() in {"completed", "failed", "skipped"}:
            self._active_step = ""
        row = {
            "timestamp": self._ts(),
            "step": step,
            "status": status_norm,
            "detail": detail,
            "active": status_norm.lower() == "running",
        }
        self.events.append(row)
        if self._on_update:
            try:
                self._on_update(self.run_id, self.to_list(), self._active_step)
            except Exception:  # noqa: BLE001
                pass
        return row

    def active_step(self) -> str:
        return self._active_step

    def to_list(self) -> list[dict[str, Any]]:
        active = self._active_step
        out: list[dict[str, Any]] = []
        for row in self.events:
            item = dict(row)
            item["active"] = bool(active and item.get("step") == active and item.get("status") == "Running")
            out.append(item)
        return out

    def summary_counts(self) -> dict[str, int]:
        return {
            "events": len(self.events),
            "completed": sum(1 for e in self.events if e.get("status") == "Completed"),
            "failed": sum(1 for e in self.events if e.get("status") == "Failed"),
            "skipped": sum(1 for e in self.events if e.get("status") == "Skipped"),
        }
