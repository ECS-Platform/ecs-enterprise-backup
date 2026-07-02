"""Gitea connector (self-hosted GitHub substitute for development).

Real connectivity via the Gitea REST API (/api/v1). Token resolves from the
GITEA_TOKEN environment variable named in integrations.yaml.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class GiteaConnector(BaseConnector):
    DEFAULT_TYPES = ["repositories", "commits", "pull_requests", "branch_protections", "releases"]

    def _apply_auth(self, client: HttpClient) -> None:
        token = self.config.secret("token_env")
        if token:
            client.with_header("Authorization", f"token {token}")

    def test_connection(self) -> ConnectorHealth:
        if not self.config.enabled or not self.config.base_url:
            return self._disabled_health()
        start = time.time()
        try:
            resp = self.http().get("/api/v1/version")
            latency = int((time.time() - start) * 1000)
            authed = False
            try:
                self.http().get("/api/v1/user")
                authed = True
            except HttpError:
                authed = False
            return self._health(connected=resp.status == 200, authenticated=authed, latency_ms=latency,
                                detail=f"gitea {resp.json().get('version', '?') if resp.body else '?'}")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _repos(self) -> list[dict[str, Any]]:
        resp = self.http().get("/api/v1/repos/search", params={"limit": self.config.page_size})
        data = resp.json() or {}
        return data.get("data", []) if isinstance(data, dict) else []

    def get_metadata(self) -> dict[str, Any]:
        repos = self._repos()
        return {"repository_count": len(repos), "repositories": [r.get("full_name") for r in repos]}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        repos = self._repos()
        for repo in repos:
            full = repo.get("full_name", "")
            owner = (repo.get("owner") or {}).get("login", "")
            if "repositories" in wanted:
                items.append(EvidenceItem(
                    source_system="gitea", source_object_id=full, object_type="repository",
                    title=f"Repository {full}", content=repo.get("description") or full,
                    collected_timestamp=utcnow(), owner=owner, url=repo.get("html_url", ""),
                    application=repo.get("name", ""),
                    metadata={"private": repo.get("private"), "default_branch": repo.get("default_branch")},
                ))
            if "pull_requests" in wanted:
                items.extend(self._pull_requests(owner, repo.get("name", "")))
            if "commits" in wanted:
                items.extend(self._commits(owner, repo.get("name", ""), repo.get("default_branch", "main")))
        return items

    def _pull_requests(self, owner: str, name: str) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        try:
            resp = self.http().get(f"/api/v1/repos/{owner}/{name}/pulls",
                                   params={"state": "all", "limit": self.config.page_size})
        except HttpError:
            return out
        for pr in resp.json() or []:
            reviews = self._pr_reviews(owner, name, pr.get("number"))
            approvals = [r for r in reviews if r.get("state") == "APPROVED"]
            out.append(EvidenceItem(
                source_system="gitea", source_object_id=f"{owner}/{name}#{pr.get('number')}",
                object_type="pull_request", title=pr.get("title", ""),
                content=(pr.get("body") or "")[:4000], collected_timestamp=utcnow(),
                owner=(pr.get("user") or {}).get("login", ""), url=pr.get("html_url", ""),
                application=name, control_mapping=["change-management", "code-review"],
                metadata={"state": pr.get("state"), "merged": pr.get("merged"),
                          "approvals": len(approvals), "reviewers": [a.get("user", {}).get("login") for a in approvals]},
            ))
        return out

    def _pr_reviews(self, owner: str, name: str, number: Any) -> list[dict[str, Any]]:
        try:
            return self.http().get(f"/api/v1/repos/{owner}/{name}/pulls/{number}/reviews").json() or []
        except HttpError:
            return []

    def _commits(self, owner: str, name: str, branch: str) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        try:
            resp = self.http().get(f"/api/v1/repos/{owner}/{name}/commits",
                                   params={"sha": branch, "limit": 20})
        except HttpError:
            return out
        for c in resp.json() or []:
            commit = c.get("commit", {})
            out.append(EvidenceItem(
                source_system="gitea", source_object_id=c.get("sha", ""), object_type="commit",
                title=(commit.get("message") or "").splitlines()[0][:200] if commit.get("message") else c.get("sha", ""),
                content=commit.get("message") or "", collected_timestamp=utcnow(),
                owner=(commit.get("author") or {}).get("name", ""), url=c.get("html_url", ""),
                application=name, control_mapping=["change-management"],
            ))
        return out
