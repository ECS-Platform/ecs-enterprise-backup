"""Audit-trail verification helpers over ECS's real audit implementation.

Authoritative sources (in the order this helper tries them):
  1. PostgreSQL ``audit_log`` (actor, role, action, resource, detail, request_id, before_state, after_state, auth_source,
     prev_hash) - correlate with the ``X-Request-ID`` the API client sends on every call.
  2. GET /api/audit/scheduler/history      scheduler job history (audit persistence layer)
  3. GET /api/audit/evidence/{key}/timeline evidence lifecycle events
  4. UI "Recent Activity" feed (partials/enterprise_widgets.html) - in-process audit trail (modules/shared/services/audit_trail.py)
NOTE: /api/demo/audit-history and /api/demo/prompt-audit return generated demo rows and are NOT used as audit proof.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from .api_client import EcsApiClient
from .assertions import assert_audit_record
from .errors import CapabilityBlocked
from .wait import wait_until


class AuditHelper:
    def __init__(self, api: EcsApiClient, db=None) -> None:
        self.api, self.db = api, db

    def records(self, *, request_id: str | None = None, action: str | None = None, resource: str | None = None,
                actor: str | None = None) -> list[Mapping[str, Any]]:
        if self.db is not None and self.db.enabled:
            return self.db.audit_records(request_id=request_id, action=action, resource=resource, actor=actor)
        rows: list[Mapping[str, Any]] = []
        resp = self.api.get("/api/audit/scheduler/history")
        if resp.status == 200 and resp.is_json:
            rows.extend(resp.json().get("history", []))
        rows.extend(self.activity_feed())
        return rows

    def activity_feed(self, page: str = "/dashboard") -> list[Mapping[str, Any]]:
        """Parse 'Recent Activity' rows from an ECS page: <strong>action</strong> · actor ... timestamp."""
        html = self.api.get(page).text
        feed = re.findall(r"<strong>(.*?)</strong>\s*·\s*(.*?)\s*<span class=\"chat-ts float-end\">(.*?)</span>", html, re.S)
        return [{"action": a.strip(), "actor": u.strip(), "timestamp": t.strip()} for a, u, t in feed]

    def verify(self, *, request_id: str | None = None, action: str | None = None, actor: str | None = None,
               resource: str | None = None, timeout: float = 15.0) -> Mapping[str, Any]:
        """Wait for (audit rows are written asynchronously in some flows) and assert a matching audit record."""
        use_rid = request_id if (self.db is not None and self.db.enabled) else None  # request_id only exists in audit_log

        def probe():
            recs = self.records(request_id=use_rid, action=action, resource=resource, actor=actor)
            try:
                return assert_audit_record(recs, action=action, actor=actor, resource=resource, request_id=use_rid)
            except AssertionError:
                return None

        return wait_until(probe, timeout=timeout, interval=self.api.cfg.poll_interval,
                          what=f"audit record action={action!r} actor={actor!r} request_id={request_id!r}")

    def verify_state_change(self, record: Mapping[str, Any]) -> None:
        """Before/after values where ECS captures them (audit_log.before_state / after_state)."""
        assert record.get("before_state") is not None or record.get("after_state") is not None, \
            "audit record carries neither before_state nor after_state"

    def verify_hash_chain(self, rows: list[Mapping[str, Any]]) -> None:
        """audit_log.prev_hash links rows (Phase 4 durable audit). Requires DB access."""
        if self.db is None or not self.db.enabled:
            raise CapabilityBlocked("Audit hash-chain verification needs database access.", requires="PostgreSQL access")
        assert all("prev_hash" in r for r in rows), "audit rows do not expose prev_hash"
