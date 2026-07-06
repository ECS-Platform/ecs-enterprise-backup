"""MongoDB connector for predefined query execution.

Uses pymongo (optional dependency — degrades gracefully if absent). Read-only:
it only issues admin/diagnostic commands (buildInfo, serverStatus, usersInfo,
listDatabases, getParameter, ...). Credential-externalised, never logs the URI or
passwords. Results normalised to ``ConnectorResult`` with a JSON-ish text body.

The catalog stores a compact "command spec" per control (e.g. ``buildInfo`` or
``getParameter:sslMode``); this connector maps that to a safe ``db.command()``.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from modules.operations.engines.query_connectors import ConnectorResult

DEFAULT_TIMEOUT_SEC = 30

# Allow-list of admin command specs the connector will run. Keys match the
# catalog `query` text. Values are (db_name, command-document builder).
_COMMAND_SPECS: dict[str, tuple[str, dict[str, Any]]] = {
    "buildInfo": ("admin", {"buildInfo": 1}),
    "serverStatus": ("admin", {"serverStatus": 1}),
    "getCmdLineOpts": ("admin", {"getCmdLineOpts": 1}),
    "getParameter:sslMode": ("admin", {"getParameter": 1, "sslMode": 1}),
    "usersInfo": ("admin", {"usersInfo": 1}),
    "rolesInfo": ("admin", {"rolesInfo": 1}),
    "listDatabases": ("admin", {"listDatabases": 1}),
    "getParameter:auditAuthorizationSuccess": ("admin", {"getParameter": 1, "auditAuthorizationSuccess": 1}),
}


def _clean(value: Any) -> str:
    s = str(value).strip() if value is not None else ""
    return "" if s.startswith("${") else s


def _safe_int(value: Any, default: int) -> int:
    try:
        s = str(value).strip()
        if not s or s.startswith("${"):
            return default
        return int(s)
    except (TypeError, ValueError):
        return default


def get_mongodb_config() -> dict[str, Any]:
    """MongoDB target for predefined query execution (env / YAML driven)."""
    from modules.operations.engines.query_connectors import get_predefined_target

    cfg = get_predefined_target("mongodb")
    uri_env = str(cfg.get("uri_env") or "ECS_MONGODB_URI")
    return {
        # URI may contain credentials; it is read from env and never logged.
        "uri": os.environ.get(uri_env) or _clean(cfg.get("uri")) or os.environ.get(
            "ECS_MONGODB_URI", "mongodb://localhost:27017"
        ),
        "database": _clean(cfg.get("database")) or os.environ.get("ECS_MONGODB_DATABASE", "admin"),
        # Container is used by diagnostics only (the connector talks over the URI).
        "container": _clean(cfg.get("container")) or os.environ.get("ECS_MONGODB_CONTAINER", "mongodb-demo"),
        "timeout_sec": _safe_int(
            cfg.get("timeout_sec")
            or os.environ.get("ECS_MONGODB_TIMEOUT_SECONDS")
            or os.environ.get("ECS_MONGODB_TIMEOUT_SEC"),
            DEFAULT_TIMEOUT_SEC,
        ),
    }


def _friendly_error(exc: Exception) -> tuple[str, str]:
    message = str(exc).strip()
    lower = message.lower()
    if "timeout" in lower or "timed out" in lower or "serverselection" in lower:
        return "timeout", "Connection/selection timed out. Ensure MongoDB is reachable."
    if "auth" in lower or "not authorized" in lower or "credentials" in lower:
        return "authentication_failure", "Authentication failed. Verify MongoDB credentials."
    if "connection refused" in lower or "no route" in lower or "connect" in lower:
        return "connection_failure", "Could not connect to MongoDB. Ensure the endpoint is reachable."
    return "query_failure", f"MongoDB error: {message}"


def _format_doc(doc: Any) -> str:
    try:
        return json.dumps(doc, indent=2, default=str)
    except Exception:  # noqa: BLE001
        return str(doc)


class MongoDBConnector:
    """Live MongoDB execution for predefined admin/diagnostic commands (pymongo)."""

    technology = "MongoDB"

    def __init__(self, uri: str = "mongodb://localhost:27017", database: str = "admin",
                 container: str = "", timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.uri = uri
        self.database = database
        # Container name is carried for diagnostics only; execution uses the URI.
        self.container = container
        self.timeout_sec = timeout_sec
        self._client = None
        self._last_error = ""

    def connect(self) -> bool:
        try:
            import pymongo
        except ImportError:
            self._last_error = "MongoDB driver (pymongo) is not installed in this environment."
            self._client = None
            return False
        try:
            self._client = pymongo.MongoClient(
                self.uri, serverSelectionTimeoutMS=min(self.timeout_sec, 10) * 1000,
            )
            # Force a round-trip so unreachable servers fail here, not mid-execute.
            self._client.admin.command("ping")
            return True
        except Exception as exc:  # noqa: BLE001
            _, self._last_error = _friendly_error(exc)
            self._client = None
            return False

    def execute(self, query: str) -> ConnectorResult:
        if not self._client:
            return ConnectorResult(
                success=False, error_message=self._last_error or "Not connected to MongoDB",
            )
        spec = _COMMAND_SPECS.get((query or "").strip())
        if not spec:
            return ConnectorResult(
                success=False,
                error_message="This MongoDB command is not enabled for live execution.",
                metadata={"error_type": "unsupported_query"},
            )
        db_name, command = spec
        started = time.perf_counter()
        try:
            result = self._client[db_name].command(command)
            output = _format_doc(result)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return ConnectorResult(
                success=True, output=output, duration_ms=duration_ms,
                metadata={"rows_returned": 1},
            )
        except Exception as exc:  # noqa: BLE001
            duration_ms = int((time.perf_counter() - started) * 1000)
            etype, friendly = _friendly_error(exc)
            return ConnectorResult(
                success=False, error_message=friendly, duration_ms=duration_ms,
                metadata={"error_type": etype},
            )

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
        self._client = None
