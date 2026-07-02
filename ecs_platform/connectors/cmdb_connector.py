"""CMDB connector (ServiceNow CMDB Table API) — credential-optional."""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError

_CMDB_TABLE = "cmdb_ci"
_CMDB_FIELDS = [
    "sys_id",
    "name",
    "sys_class_name",
    "owned_by",
    "support_group",
    "install_status",
    "environment",
]


class CMDBConnector(BaseConnector):
    """Collects configuration item evidence from ServiceNow CMDB."""

    DEFAULT_TYPES = ["configuration_items"]

    def _apply_auth(self, client: HttpClient) -> None:
        """Apply ServiceNow basic authentication for CMDB access."""
        # TODO:
        # CMDB_URL
        # CMDB_USER
        # CMDB_PASSWORD
        client.with_basic(self.config.secret("username_env"), self.config.secret("password_env"))

    def _configured(self) -> bool:
        """Return True when connector is enabled and credentials are present."""
        return bool(
            self.config.enabled
            and self.config.base_url
            and self.config.secret("username_env")
            and self.config.secret("password_env")
        )

    def test_connection(self) -> ConnectorHealth:
        """Validate connectivity/authentication against the CMDB table endpoint."""
        if not self._configured():
            return self._disabled_health("set CMDB_URL + CMDB_USER + CMDB_PASSWORD and enable")
        start = time.time()
        try:
            resp = self.http().get(
                f"/api/now/table/{_CMDB_TABLE}",
                params={"sysparm_limit": 1, "sysparm_fields": "sys_id"},
            )
            return self._health(
                connected=True,
                authenticated=resp.status == 200,
                latency_ms=int((time.time() - start) * 1000),
                detail="authenticated",
            )
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def get_metadata(self) -> dict[str, Any]:
        """Return connector readiness and CMDB table metadata."""
        if not self._configured():
            return {"configured": False, "table": _CMDB_TABLE}
        return {
            "configured": True,
            "table": _CMDB_TABLE,
            "fields": list(_CMDB_FIELDS),
            "page_size": self.config.page_size,
        }

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        """Collect CMDB configuration items and normalize them into evidence artifacts."""
        if not self._configured():
            return []
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        if not {"configuration_items", "configuration_item"} & wanted:
            return []

        items: list[EvidenceItem] = []
        for rec in self._iter_cmdb_records():
            sys_id = str(rec.get("sys_id") or "")
            name = str(rec.get("name") or sys_id)
            class_name = str(rec.get("sys_class_name") or "configuration_item")
            owner = self._display_value(rec.get("owned_by"))
            support_group = self._display_value(rec.get("support_group"))
            install_status = self._display_value(rec.get("install_status"))
            environment = self._display_value(rec.get("environment"))

            items.append(
                EvidenceItem(
                    source_system="cmdb",
                    source_object_id=sys_id,
                    object_type="configuration_item",
                    title=f"Configuration Item {name}",
                    content=f"{name} ({class_name})",
                    collected_timestamp=utcnow(),
                    owner=owner,
                    application=name,
                    url=f"{self.config.base_url.rstrip('/')}/nav_to.do?uri={_CMDB_TABLE}.do?sys_id={sys_id}",
                    metadata={
                        "sys_class_name": class_name,
                        "owned_by": owner,
                        "support_group": support_group,
                        "install_status": install_status,
                        "environment": environment,
                    },
                )
            )
        return items

    def _iter_cmdb_records(self) -> Iterable[dict[str, Any]]:
        """Yield CMDB records page-by-page from the ServiceNow Table API."""
        offset = 0
        page_size = max(1, int(self.config.page_size))
        fields = ",".join(_CMDB_FIELDS)
        while True:
            try:
                resp = self.http().get(
                    f"/api/now/table/{_CMDB_TABLE}",
                    params={
                        "sysparm_fields": fields,
                        "sysparm_limit": page_size,
                        "sysparm_offset": offset,
                    },
                )
            except HttpError:
                return
            rows = (resp.json() or {}).get("result", [])
            if not rows:
                return
            for row in rows:
                if isinstance(row, dict):
                    yield row
            if len(rows) < page_size:
                return
            offset += page_size

    @staticmethod
    def _display_value(value: Any) -> str:
        """Return a best-effort string for ServiceNow reference/simple field values."""
        if isinstance(value, dict):
            return str(value.get("display_value") or value.get("value") or "")
        return str(value or "")
