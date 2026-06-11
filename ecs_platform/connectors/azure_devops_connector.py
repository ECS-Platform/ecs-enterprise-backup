"""Azure DevOps connector — real REST endpoints (PAT auth), credential-optional."""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class AzureDevOpsConnector(BaseConnector):
    DEFAULT_TYPES = ["repositories", "pull_requests", "pipelines"]
    _API = "api-version=7.1"

    def _apply_auth(self, client: HttpClient) -> None:
        client.with_basic("", self.config.secret("token_env"))  # PAT as basic password

    @property
    def _org(self) -> str:
        return str(self.config.options.get("organization", "") or "")

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url and self.config.secret("token_env") and self._org)

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set AZDO_URL + AZDO_ORG + AZDO_TOKEN and enable")
        start = time.time()
        try:
            resp = self.http().get(f"/{self._org}/_apis/projects?{self._API}")
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000), detail="authenticated")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _projects(self) -> list[dict[str, Any]]:
        try:
            return (self.http().get(f"/{self._org}/_apis/projects?{self._API}").json() or {}).get("value", [])
        except HttpError:
            return []

    def get_metadata(self) -> dict[str, Any]:
        if not self._configured():
            return {"configured": False}
        return {"configured": True, "project_count": len(self._projects())}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._configured():
            return []
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        for proj in self._projects():
            name = proj.get("name", "")
            if "repositories" in wanted:
                items.extend(self._repos(name))
        return items

    def _repos(self, project: str) -> list[EvidenceItem]:
        try:
            repos = (self.http().get(f"/{self._org}/{project}/_apis/git/repositories?{self._API}").json() or {}).get("value", [])
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for repo in repos:
            out.append(EvidenceItem(
                source_system="azure_devops", source_object_id=repo.get("id", ""), object_type="repository",
                title=repo.get("name", ""), content=f"{project}/{repo.get('name', '')}",
                collected_timestamp=utcnow(), application=project, url=repo.get("webUrl", ""),
                control_mapping=["change-management"],
            ))
        return out
