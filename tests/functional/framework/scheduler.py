"""Scheduler capabilities over the REAL ECS schedulers (no scheduler is created by the framework).

ECS exposes three scheduler surfaces, all reused here:
  1. Collection scheduler (modules/operations/engines/scheduler_module.py)
       POST /mvp/scheduler/run  (JSON via header X-ECS-Scheduler-JSON: 1; sync via X-ECS-Scheduler-Sync: 1)
       GET  /mvp/scheduler/run-status?run_id=   POST /mvp/scheduler/{retry,pause,resume}   GET /mvp/scheduler
  2. Governance schedules (ecs_platform.governance; table collection_schedules)
       GET/POST /mvp/platform/scheduler  (form: name, connector, app_slug, frequency, owner)
  3. Audit-intelligence asset scheduler (modules/audit_intelligence/routes)
       GET /api/audit/scheduler/{plan,history,queue,dead-letter}   POST /api/audit/scheduler/{dry-run,execute,execute-parallel}
       POST /api/audit/scheduler/dead-letter/{item_id}/requeue
ECS has NO schedule update/delete API and no cron-expression field; those capabilities raise CapabilityBlocked.
"""

from __future__ import annotations

import re
from typing import Any

from .api_client import ApiResponse, EcsApiClient
from .data_factory import DataFactory
from .errors import CapabilityBlocked
from .wait import wait_for_scheduler_execution


class SchedulerHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory, db=None) -> None:
        self.api, self.data, self.db = api, data, db
        self.runs: list[str] = []

    # ---- governance schedules (create / list) -------------------------------------------------------------
    def create_schedule(self, **overrides: Any) -> tuple[dict[str, Any], ApiResponse]:
        """POST /mvp/platform/scheduler. Returns (schedule_fields, response); success notice is "Schedule '<name>' created."."""
        fields = self.data.schedule(**overrides)
        persona = self.api.persona_key or "compliance_head"
        resp = self.api.as_persona(persona).post("/mvp/platform/scheduler", data=fields)
        return fields, resp

    def list_schedules_page(self) -> ApiResponse:
        return self.api.get("/mvp/platform/scheduler")

    def schedule_row(self, name: str) -> dict[str, Any] | None:
        """DB record in collection_schedules (requires DB validation enabled)."""
        return self.db.one("collection_schedules", name=name) if self.db else None

    def schedule_visible_in_ui(self, name: str) -> bool:
        return name in self.list_schedules_page().text

    def update_schedule(self, *_a: Any, **_k: Any) -> None:
        raise CapabilityBlocked("ECS has no schedule update/delete endpoint (only POST /mvp/platform/scheduler upsert by name).",
                                requires="schedule update API")

    # ---- collection run ---------------------------------------------------------------------------------------------
    def run_collection(self, *, applications: list[str] | None = None, frameworks: list[str] | None = None,
                       sync: bool = False, persona: str | None = None) -> ApiResponse:
        """POST /mvp/scheduler/run as JSON. Async by default (returns run_id to poll with run_status)."""
        client = self.api.as_persona(persona) if persona else self.api
        headers = {"X-ECS-Scheduler-JSON": "1"}
        if sync:
            headers["X-ECS-Scheduler-Sync"] = "1"
        resp = client.post("/mvp/scheduler/run", headers=headers,
                           data={"applications": applications or [self.data.application()],
                                 "frameworks": frameworks or [self.data.framework()]})
        rid = run_id_of(resp)
        if rid:
            self.runs.append(rid)
        return resp

    def run_status(self, run_id: str) -> dict[str, Any]:
        resp = self.api.get("/mvp/scheduler/run-status", params={"run_id": run_id})
        return resp.json() if resp.is_json else {"status": "unknown", "http": resp.status}

    def wait_for_run(self, run_id: str, timeout: float | None = None) -> dict[str, Any]:
        return wait_for_scheduler_execution(self, run_id, timeout=timeout or self.api.cfg.long_timeout,
                                            interval=self.api.cfg.poll_interval)

    def execute_and_wait(self, **kw: Any) -> dict[str, Any]:
        resp = self.run_collection(**kw)
        assert resp.status < 400, f"scheduler run rejected: {resp.status} {resp.text[:200]}"
        rid = run_id_of(resp)
        assert rid, f"no run_id in scheduler response: {resp.text[:200]}"
        return self.wait_for_run(rid)

    def retry(self, failure_id: str) -> ApiResponse:
        return self.api.post("/mvp/scheduler/retry", data={"failure_id": failure_id})

    def pause(self) -> ApiResponse:
        return self.api.post("/mvp/scheduler/pause")

    def resume(self) -> ApiResponse:
        return self.api.post("/mvp/scheduler/resume")

    def dashboard(self) -> ApiResponse:
        return self.api.get("/mvp/scheduler")

    # ---- audit-intelligence asset scheduler ----------------------------------------------------------------------------
    def plan(self) -> dict[str, Any]:
        return self.api.get_json("/api/audit/scheduler/plan")

    def dry_run(self, **payload: Any) -> ApiResponse:
        return self.api.post("/api/audit/scheduler/dry-run", json=payload)

    def history(self, limit: int = 100) -> list[dict]:
        body = self.api.get_json("/api/audit/scheduler/history", params={"limit": limit})
        return body.get("history", []) if isinstance(body, dict) else []

    def queue(self) -> dict[str, Any]:
        return self.api.get_json("/api/audit/scheduler/queue")

    def dead_letter(self) -> dict[str, Any]:
        return self.api.get_json("/api/audit/scheduler/dead-letter")

    def requeue_dead_letter(self, item_id: str, persona: str = "system_admin") -> ApiResponse:
        return self.api.as_persona(persona).post(f"/api/audit/scheduler/dead-letter/{item_id}/requeue", json={})

    def execute_baseline(self, persona: str = "system_admin", **payload: Any) -> ApiResponse:
        """POST /api/audit/scheduler/execute (platform-admin only; baseline jobs, connectors stay off)."""
        return self.api.as_persona(persona).post("/api/audit/scheduler/execute", json=payload)

    def execute_parallel(self, persona: str = "system_admin", **payload: Any) -> ApiResponse:
        return self.api.as_persona(persona).post("/api/audit/scheduler/execute-parallel", json=payload)

    def next_run(self, schedule_name: str) -> Any:
        row = self.schedule_row(schedule_name)
        return row.get("next_run") if row else None

    def execution_history_rows(self) -> list[dict]:
        """Sync runs recorded by ECS (sync_runs table), newest first."""
        return self.db.find("sync_runs", order_by="started_at DESC") if self.db else []


def run_id_of(resp: ApiResponse) -> str:
    if resp.is_json:
        body = resp.json()
        if isinstance(body, dict):
            return str(body.get("run_id") or (body.get("summary") or {}).get("run_id") or "")
    m = re.search(r"run_id=([\w\-:.]+)", resp.location or "")
    return m.group(1) if m else ""
