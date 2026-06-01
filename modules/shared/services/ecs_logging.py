"""Centralized ECS terminal logging — UTC timestamps, module tags, readable colors."""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_RESET = "\033[0m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
}

_MARKER_PATH = Path(__file__).resolve().parent.parent / ".ecs_boot_marker"
_startup_complete = False
_configured = False


class _ECSFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        module = getattr(record, "ecs_module", "ECS")
        color = _LEVEL_COLORS.get(record.levelno, "")
        level = f"{color}{record.levelname}{_RESET}" if color else record.levelname
        return f"[{ts}] {level} [{module}] {record.getMessage()}"


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    root = logging.getLogger("ecs")
    root.setLevel(level)
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ECSFormatter())
    root.addHandler(handler)
    root.propagate = False
    _configured = True


def _emit(level: int, module: str, message: str) -> None:
    configure_logging()
    logging.getLogger("ecs").log(level, message, extra={"ecs_module": module})


def is_ready() -> bool:
    return _startup_complete


def mark_startup_complete() -> None:
    global _startup_complete
    _startup_complete = True


def _record_boot() -> int:
    data: dict = {"ts": time.time(), "boots": 0}
    if _MARKER_PATH.exists():
        try:
            data = json.loads(_MARKER_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    data["ts"] = time.time()
    data["boots"] = int(data.get("boots", 0)) + 1
    try:
        _MARKER_PATH.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass
    return data["boots"]


def detect_reload() -> bool:
    if not _MARKER_PATH.exists():
        return False
    try:
        data = json.loads(_MARKER_PATH.read_text(encoding="utf-8"))
        return int(data.get("boots", 0)) >= 1 and (time.time() - float(data.get("ts", 0))) < 180
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return False


def log_platform_ready(host: str = "127.0.0.1", port: int = 8000) -> None:
    configure_logging()
    is_reload = detect_reload()
    boot_count = _record_boot()

    if is_reload:
        _emit(logging.INFO, "Reload", "Code changes applied — ECS platform reload complete.")
        _emit(logging.INFO, "Reload", "Browser refresh recommended if the UI was open.")
    else:
        sep = "=" * 52
        _emit(logging.INFO, "Startup", sep)
        _emit(logging.INFO, "Startup", "ECS Enterprise Platform Ready")
        _emit(logging.INFO, "Startup", f"URL: http://{host}:{port}")
        _emit(logging.INFO, "Startup", "Startup completed successfully")
        _emit(logging.INFO, "Startup", sep)

    if boot_count > 1 and not is_reload:
        _emit(logging.INFO, "Startup", f"Process boot #{boot_count} — application stable.")


def info(module: str, message: str) -> None:
    _emit(logging.INFO, module, message)


def warning(module: str, message: str) -> None:
    _emit(logging.WARNING, module, message)


def error(module: str, message: str) -> None:
    _emit(logging.ERROR, module, message)


def debug(module: str, message: str) -> None:
    _emit(logging.DEBUG, module, message)


_QUIET_ACTIONS = frozenset({
    "Viewed Evidence",
    "Owner Comment Added",
    "Draft Saved",
    "Draft Cancelled",
})


def log_workflow_event(
    action: str,
    actor: str,
    framework: str = "",
    control: str = "",
    detail: str = "",
    role: str = "",
) -> None:
    if not _startup_complete:
        return

    level = logging.DEBUG if action in _QUIET_ACTIONS else logging.INFO
    module = "Workflow"
    if "Integration" in action or "Sync" in action:
        module = "Integration"
    elif "Scheduled Pull" in action or "Scheduler" in actor:
        module = "Scheduler"

    who = f"{actor} ({role})" if role else actor
    parts = [action, f"by {who}"]
    if framework:
        loc = framework if not control else f"{framework} / {control[:60]}"
        parts.append(f"— {loc}")
    if detail:
        parts.append(f"— {detail[:100]}")

    _emit(level, module, " ".join(parts))


def log_login(role: str, user: str, destination: str = "") -> None:
    if not _startup_complete:
        return
    dest = f" → {destination}" if destination else ""
    info("Login", f"{user} logged in as {role}{dest}")


def log_navigation(user: str, role: str, target: str) -> None:
    if not _startup_complete:
        return
    info("Navigation", f"{user} ({role}) opened {target}")


def log_chatbot(user: str, role: str, query: str, framework: str = "") -> None:
    if not _startup_complete:
        return
    fw = f" [{framework}]" if framework else ""
    preview = query.strip().replace("\n", " ")[:90]
    info("Chatbot", f"{user} ({role}){fw}: {preview}")


def log_integration(connector: str, action: str = "sync", user: str = "", records: int | None = None) -> None:
    if not _startup_complete:
        return
    extra = f" — {records} records" if records is not None else ""
    who = f" by {user}" if user else ""
    info("Integration", f"{connector} {action} completed{extra}{who}")


def log_scheduler(action: str, detail: str = "", user: str = "") -> None:
    if not _startup_complete:
        return
    who = f" by {user}" if user else ""
    info("Scheduler", f"{action}{who}" + (f" — {detail}" if detail else ""))


def log_export(user: str, report_id: str) -> None:
    if not _startup_complete:
        return
    info("Export", f"Report {report_id} downloaded by {user}")
