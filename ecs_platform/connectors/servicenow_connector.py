"""ServiceNow connector — real Table API endpoints, credential-optional."""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError

# object_type -> ServiceNow table
_TABLES = {
    "incidents": "incident",
    "change_requests": "change_request",
    "problem_records": "problem",
    "cab_approvals": "sysapproval_approver",
}


class ServiceNowConnector(BaseConnector):
    DEFAULT_TYPES = ["change_requests", "incidents"]

    def _apply_auth(self, client: HttpClient) -> None:
        client.with_basic(self.config.secret("username_env"), self.config.secret("password_env"))

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url
                    and self.config.secret("username_env") and self.config.secret("password_env"))

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set SNOW_URL + SNOW_USER + SNOW_PASSWORD and enable")
        start = time.time()
        try:
            resp = self.http().get("/api/now/table/change_request", params={"sysparm_limit": 1})
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000), detail="authenticated")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def get_metadata(self) -> dict[str, Any]:
        return {"configured": self._configured(), "tables": list(_TABLES.values())}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._configured():
            return []
        wanted = list(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        for obj in wanted:
            table = _TABLES.get(obj)
            if not table:
                continue
            items.extend(self._records(obj, table))
        return items

    def _records(self, obj: str, table: str) -> list[EvidenceItem]:
        try:
            resp = self.http().get(f"/api/now/table/{table}", params={"sysparm_limit": self.config.page_size})
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for rec in (resp.json() or {}).get("result", []):
            num = rec.get("number") or rec.get("sys_id", "")
            out.append(EvidenceItem(
                source_system="servicenow", source_object_id=num, object_type=obj.rstrip("s"),
                title=f"{table} {num}", content=rec.get("short_description", "") or rec.get("description", ""),
                collected_timestamp=utcnow(), application=table,
                url=f"{self.config.base_url.rstrip('/')}/nav_to.do?uri={table}.do?sys_id={rec.get('sys_id')}",
                control_mapping=["change-management"], framework_mapping=["ITIL", "SOC2-CC8"],
                metadata={"state": rec.get("state"), "approval": rec.get("approval")},
            ))
        return out
