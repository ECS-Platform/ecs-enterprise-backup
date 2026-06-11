"""Prisma Cloud connector — real auth + findings endpoints, credential-optional.

Prisma issues a JWT from access_key/secret_key via POST /login; the token is then
sent as the x-redlock-auth header.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class PrismaConnector(BaseConnector):
    DEFAULT_TYPES = ["cloud_findings", "compliance_violations"]

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url
                    and self.config.secret("access_key_env") and self.config.secret("secret_key_env"))

    def _login(self) -> str:
        resp = self.http().post("/login", json_body={
            "username": self.config.secret("access_key_env"),
            "password": self.config.secret("secret_key_env"),
        })
        return (resp.json() or {}).get("token", "")

    def _authed_client(self) -> HttpClient:
        token = self._login()
        client = HttpClient(base_url=self.config.base_url, timeout_sec=self.config.timeout_sec,
                            max_retries=self.config.max_retries, verify_ssl=self.config.verify_ssl)
        return client.with_header("x-redlock-auth", token)

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set PRISMA_URL + PRISMA_ACCESS_KEY + PRISMA_SECRET_KEY and enable")
        start = time.time()
        try:
            token = self._login()
            return self._health(connected=True, authenticated=bool(token),
                                latency_ms=int((time.time() - start) * 1000), detail="authenticated")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def get_metadata(self) -> dict[str, Any]:
        return {"configured": self._configured()}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._configured():
            return []
        items: list[EvidenceItem] = []
        try:
            client = self._authed_client()
            alerts = client.get("/v2/alert", params={"limit": self.config.page_size}).json() or {}
        except HttpError:
            return []
        for alert in (alerts.get("items", []) if isinstance(alerts, dict) else alerts)[: self.config.page_size]:
            policy = alert.get("policy", {}) if isinstance(alert, dict) else {}
            items.append(EvidenceItem(
                source_system="prisma", source_object_id=str(alert.get("id", "")),
                object_type="cloud_finding", title=policy.get("name", "Cloud finding"),
                content=policy.get("description", ""), collected_timestamp=utcnow(),
                control_mapping=["cloud-security", "vulnerability-management"],
                framework_mapping=["SOC2-CC7"],
                metadata={"severity": policy.get("severity"), "status": alert.get("status")},
            ))
        return items
