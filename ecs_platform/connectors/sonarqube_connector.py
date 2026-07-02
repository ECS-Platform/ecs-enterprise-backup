"""SonarQube connector (self-hosted) — real connectivity via Web API.

Auth: token via Bearer (SonarQube >= 10) or token-as-username basic, with
optional user/password fallback for fresh local instances.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class SonarQubeConnector(BaseConnector):
    DEFAULT_TYPES = ["quality_gates", "coverage", "vulnerabilities", "code_smells", "security_hotspots"]
    _METRICS = "bugs,vulnerabilities,code_smells,coverage,security_hotspots,alert_status,ncloc"

    def _apply_auth(self, client: HttpClient) -> None:
        token = self.config.secret("token_env")
        if token:
            client.with_basic(token, "")  # SonarQube: token as username, empty password
            return
        user = self.config.secret("username_env")
        pwd = self.config.secret("password_env")
        if user or pwd:
            client.with_basic(user, pwd)

    def test_connection(self) -> ConnectorHealth:
        if not self.config.enabled or not self.config.base_url:
            return self._disabled_health()
        start = time.time()
        try:
            status = self.http().get("/api/system/status")
            latency = int((time.time() - start) * 1000)
            authed = False
            try:
                self.http().get("/api/authentication/validate")
                authed = True
            except HttpError:
                authed = False
            payload = status.json() or {}
            return self._health(connected=payload.get("status") == "UP", authenticated=authed,
                                latency_ms=latency, detail=f"sonarqube {payload.get('version', '?')}")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _projects(self) -> list[dict[str, Any]]:
        try:
            resp = self.http().get("/api/projects/search", params={"ps": self.config.page_size})
            return (resp.json() or {}).get("components", [])
        except HttpError:
            return []

    def get_metadata(self) -> dict[str, Any]:
        projects = self._projects()
        return {"project_count": len(projects), "projects": [p.get("key") for p in projects]}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        for project in self._projects():
            key = project.get("key", "")
            measures = self._measures(key)
            if {"quality_gates", "coverage", "code_smells", "vulnerabilities"} & wanted:
                items.append(EvidenceItem(
                    source_system="sonarqube", source_object_id=key, object_type="quality_gate",
                    title=f"Quality measures for {project.get('name', key)}",
                    content="; ".join(f"{k}={v}" for k, v in measures.items()),
                    collected_timestamp=utcnow(), application=project.get("name", key),
                    url=f"{self.config.base_url.rstrip('/')}/dashboard?id={key}",
                    control_mapping=["secure-sdlc", "code-quality"],
                    framework_mapping=["SOC2-CC8", "ISO27001-A.14"], metadata=measures,
                ))
            if "security_hotspots" in wanted:
                items.extend(self._hotspots(key, project.get("name", key)))
        return items

    def _measures(self, key: str) -> dict[str, Any]:
        try:
            resp = self.http().get("/api/measures/component",
                                   params={"component": key, "metricKeys": self._METRICS})
        except HttpError:
            return {}
        comp = (resp.json() or {}).get("component", {})
        return {m.get("metric"): m.get("value") for m in comp.get("measures", [])}

    def _hotspots(self, key: str, name: str) -> list[EvidenceItem]:
        try:
            resp = self.http().get("/api/hotspots/search", params={"projectKey": key, "ps": 50})
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for h in (resp.json() or {}).get("hotspots", []):
            out.append(EvidenceItem(
                source_system="sonarqube", source_object_id=h.get("key", ""),
                object_type="security_hotspot", title=h.get("message", "")[:200],
                content=h.get("message", ""), collected_timestamp=utcnow(), application=name,
                control_mapping=["vulnerability-management"], framework_mapping=["SOC2-CC7"],
                metadata={"status": h.get("status"), "vulnerabilityProbability": h.get("vulnerabilityProbability")},
            ))
        return out
