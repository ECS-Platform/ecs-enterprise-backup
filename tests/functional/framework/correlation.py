"""Cross-component correlation of identifiers for asynchronous ECS workflows.

UI/API request -> scheduler -> connector -> ingestion -> processing -> database -> object storage -> audit -> notification -> dashboard

Identifiers are recorded ONLY where ECS actually produces them:
  request_id   X-Request-ID echoed by ECS, stored in audit_log.request_id
  run_id       scheduler collection run (/mvp/scheduler/run)           job_id / execution_id  scheduler & audit-run ids
  evidence_id  display evidence id (/evidence/upload)                  evidence_uid  evidence.evidence_uid
  application / control / framework   catalogue keys                   audit_id  audit_log.id
Execution-id / job-id aliases map to ECS's run_id (ECS has no separate execution identifier).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ALIASES = {"execution_id": "run_id", "job_id": "run_id"}


@dataclass
class CorrelationTracker:
    ids: dict[str, list[str]] = field(default_factory=dict)

    def add(self, kind: str, value: Any) -> None:
        kind = ALIASES.get(kind, kind)
        if value in (None, ""):
            return
        bucket = self.ids.setdefault(kind, [])
        if str(value) not in bucket:
            bucket.append(str(value))

    def from_response(self, resp) -> None:
        self.add("request_id", resp.request_id)
        if resp.is_json:
            try:
                body = resp.json()
            except AssertionError:
                return
            if isinstance(body, dict):
                for k in ("run_id", "evidence_id", "repository_id", "evidence_uid", "evidence_key", "audit_id", "observation_id"):
                    self.add(k, body.get(k))

    def from_audit(self, rows) -> None:
        for r in rows:
            self.add("audit_id", r.get("id"))
            self.add("request_id", r.get("request_id"))

    def last(self, kind: str) -> str:
        vals = self.ids.get(ALIASES.get(kind, kind), [])
        return vals[-1] if vals else ""

    def snapshot(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.ids.items()}
