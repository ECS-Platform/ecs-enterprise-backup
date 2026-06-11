"""Jira connector (Atlassian Cloud / Data Center) — real REST v3 endpoints.

Credential-optional: disabled until JIRA_URL + JIRA_USER + JIRA_TOKEN are set.
Atlassian Cloud uses basic auth with email + API token.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class JiraConnector(BaseConnector):
    DEFAULT_TYPES = ["projects", "issues", "approvals"]

    def _apply_auth(self, client: HttpClient) -> None:
        user = self.config.secret("username_env")
        token = self.config.secret("token_env")
        if user and token:
            client.with_basic(user, token)
        elif token:
            client.with_bearer(token)

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url and self.config.secret("token_env"))

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set JIRA_URL + JIRA_USER + JIRA_TOKEN and enable to activate")
        start = time.time()
        try:
            resp = self.http().get("/rest/api/3/myself")
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000),
                                detail=(resp.json() or {}).get("displayName", "authenticated"))
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _projects(self) -> list[dict[str, Any]]:
        try:
            return (self.http().get("/rest/api/3/project/search",
                                    params={"maxResults": self.config.page_size}).json() or {}).get("values", [])
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
            key = proj.get("key", "")
            if "projects" in wanted:
                items.append(EvidenceItem(
                    source_system="jira", source_object_id=key, object_type="project",
                    title=f"Jira project {proj.get('name', key)}", content=proj.get("name", key),
                    collected_timestamp=utcnow(), application=key,
                    url=f"{self.config.base_url.rstrip('/')}/browse/{key}",
                ))
            if {"issues", "stories", "epics", "approvals"} & wanted:
                items.extend(self._issues(key))
        return items

    def _search_issues(self, project_key: str) -> dict[str, Any]:
        """Official Jira issue search.

        Jira Cloud removed the legacy GET /rest/api/3/search (deprecation completed
        May 2025); the current endpoint is /rest/api/3/search/jql. We try it first
        and fall back to the legacy endpoint for Jira Server/Data Center.
        """
        params = {"jql": f"project={project_key} ORDER BY updated DESC",
                  "maxResults": self.config.page_size,
                  "fields": "summary,status,issuetype,assignee,resolution"}
        try:
            return self.http().get("/rest/api/3/search/jql", params=params).json() or {}
        except HttpError as exc:
            if exc.status in (404, 410, 405):  # not present on this deployment -> legacy
                try:
                    return self.http().get("/rest/api/3/search", params=params).json() or {}
                except HttpError:
                    return {}
            return {}

    def _issues(self, project_key: str) -> list[EvidenceItem]:
        resp_json = self._search_issues(project_key)
        out: list[EvidenceItem] = []
        for issue in resp_json.get("issues", []):
            f = issue.get("fields", {})
            out.append(EvidenceItem(
                source_system="jira", source_object_id=issue.get("key", ""),
                object_type=(f.get("issuetype") or {}).get("name", "issue").lower(),
                title=f.get("summary", ""), content=f.get("summary", ""), collected_timestamp=utcnow(),
                owner=(f.get("assignee") or {}).get("displayName", ""), application=project_key,
                url=f"{self.config.base_url.rstrip('/')}/browse/{issue.get('key')}",
                control_mapping=["change-management"],
                metadata={"status": (f.get("status") or {}).get("name"),
                          "resolution": (f.get("resolution") or {}).get("name")},
            ))
        return out
