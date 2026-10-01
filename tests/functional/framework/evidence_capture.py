"""Failure-evidence capture hooks (wired by conftest.py; they only run when a test has FAILED during a real execution).

Captured per failing test, under ``tests/functional/reports/evidence/<test_id>/``:
  api_history.json  - last API requests/responses made by the test (method, url, status, request_id, snippets)
  correlation.json  - request_id / run_id / evidence_id / audit_id ... recorded by the CorrelationTracker
  db_records.json   - evidence + audit_log rows for the correlated ids (only when DB validation is enabled)
  logs.txt          - tail of the ECS backend log (ECS_FT_LOG_FILE) when configured
  error.txt         - failure message / traceback text
  screenshot.png    - UI screenshot when a UI session was used
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


def _tail(path: str, lines: int = 200) -> str:
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 65536))
            return "\n".join(fh.read().decode("utf-8", errors="replace").splitlines()[-lines:])
    except OSError as exc:
        return f"<log unavailable: {exc}>"


def capture_failure(ctx, test_id: str, error_text: str) -> dict[str, Any]:
    out = REPORTS_DIR / "evidence" / test_id
    out.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"test_id": test_id}

    def dump(name: str, payload: Any) -> None:
        (out / name).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        manifest[name] = str(out / name)

    (out / "error.txt").write_text(error_text, encoding="utf-8")
    dump("api_history.json", ctx.api.history[-50:])
    dump("correlation.json", ctx.correlation.snapshot())
    if ctx.db.enabled:
        try:
            rows: dict[str, Any] = {}
            for rid in ctx.correlation.ids.get("request_id", [])[-10:]:
                rows.setdefault("audit_log", []).extend(ctx.db.audit_records(request_id=rid))
            for uid in ctx.correlation.ids.get("evidence_uid", [])[-5:]:
                rows.setdefault("evidence", []).extend(ctx.db.evidence(evidence_uid=uid))
            dump("db_records.json", rows)
        except Exception as exc:  # noqa: BLE001 - capture must never mask the real failure
            manifest["db_records_error"] = str(exc)
    log_file = ctx.cfg.get("hooks.log_file")
    if log_file:
        (out / "logs.txt").write_text(_tail(str(log_file)), encoding="utf-8")
        manifest["logs.txt"] = str(out / "logs.txt")
    if ctx.ui_session is not None:
        shot = ctx.ui_session.screenshot(test_id)
        if shot:
            manifest["screenshot"] = str(shot)
    return manifest
