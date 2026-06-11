"""Figma connector (Figma REST API v1) — real connectivity, credential-optional.

Disabled until FIGMA_TOKEN + FIGMA_TEAM_IDS are set and enabled: true. No code
change is required to onboard a tenant.

Auth: Figma personal access token sent via the `X-Figma-Token` header.
Hierarchy: Team -> Projects -> Files. /v1/me has no team listing, so one or more
team ids must be supplied via the `team_ids` option (comma-separated env value).
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class FigmaConnector(BaseConnector):
    DEFAULT_TYPES = ["design_projects", "design_files"]

    def _apply_auth(self, client: HttpClient) -> None:
        token = self.config.secret("token_env")
        if token:
            client.with_header("X-Figma-Token", token)

    def _team_ids(self) -> list[str]:
        raw = str(self.config.env("team_ids_env") or self.config.options.get("team_ids", "") or "")
        return [t.strip() for t in raw.replace(";", ",").split(",") if t.strip()]

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url and self.config.secret("token_env"))

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set FIGMA_TOKEN (+ FIGMA_TEAM_IDS) and enable to activate")
        start = time.time()
        try:
            resp = self.http().get("/v1/me")
            who = (resp.json() or {}).get("handle") or (resp.json() or {}).get("email") or "authenticated"
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000), detail=str(who))
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _projects(self, team_id: str) -> list[dict[str, Any]]:
        try:
            return (self.http().get(f"/v1/teams/{team_id}/projects").json() or {}).get("projects", [])
        except HttpError:
            return []

    def _files(self, project_id: str) -> list[dict[str, Any]]:
        try:
            return (self.http().get(f"/v1/projects/{project_id}/files").json() or {}).get("files", [])
        except HttpError:
            return []

    def get_metadata(self) -> dict[str, Any]:
        if not self._configured():
            return {"configured": False}
        teams = self._team_ids()
        projects = sum(len(self._projects(t)) for t in teams)
        return {"configured": True, "team_count": len(teams), "project_count": projects}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._configured():
            return []
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        for team_id in self._team_ids():
            for proj in self._projects(team_id):
                pid = str(proj.get("id", ""))
                pname = proj.get("name", pid)
                if {"design_projects", "projects"} & wanted:
                    items.append(EvidenceItem(
                        source_system="figma", source_object_id=f"project:{pid}",
                        object_type="design_project", title=f"Figma project {pname}",
                        content=pname, collected_timestamp=utcnow(), application=pname,
                        url=f"https://www.figma.com/files/project/{pid}",
                        control_mapping=["design-review", "secure-design"],
                        framework_mapping=["SOC2-CC8"], metadata={"team_id": team_id},
                    ))
                if {"design_files", "files", "prototypes", "design_reviews"} & wanted:
                    items.extend(self._file_items(pid, pname, team_id))
        return items

    def _file_items(self, project_id: str, project_name: str, team_id: str) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        for f in self._files(project_id):
            key = f.get("key", "")
            out.append(EvidenceItem(
                source_system="figma", source_object_id=f"file:{key}",
                object_type="design_file", title=f.get("name", key),
                content=f.get("name", key), collected_timestamp=utcnow(),
                application=project_name, url=f"https://www.figma.com/file/{key}",
                control_mapping=["design-review", "secure-design"],
                framework_mapping=["SOC2-CC8"],
                metadata={"project_id": project_id, "team_id": team_id,
                          "last_modified": f.get("last_modified"),
                          "thumbnail_url": f.get("thumbnail_url")},
            ))
        return out
