"""GitHub Enterprise / github.com connector (real REST v3).

Credential-optional: disabled until GITHUB_TOKEN + org are configured. No code
change is required to onboard — set env vars and enabled: true in integrations.yaml.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class GitHubConnector(BaseConnector):
    DEFAULT_TYPES = ["repositories", "pull_requests", "branch_protections"]

    def _apply_auth(self, client: HttpClient) -> None:
        token = self.config.secret("token_env")
        if token:
            client.with_bearer(token)
        client.with_header("X-GitHub-Api-Version", "2022-11-28")

    @property
    def _org(self) -> str:
        return str(self.config.options.get("org", "") or "")

    def _configured(self) -> bool:
        return bool(self.config.enabled and self.config.base_url and self.config.secret("token_env") and self._org)

    def test_connection(self) -> ConnectorHealth:
        if not self._configured():
            return self._disabled_health("set GITHUB_TOKEN + GITHUB_ORG and enable to activate")
        start = time.time()
        try:
            resp = self.http().get(f"/orgs/{self._org}")
            return self._health(connected=True, authenticated=resp.status == 200,
                                latency_ms=int((time.time() - start) * 1000), detail=f"org {self._org}")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _repos(self) -> list[dict[str, Any]]:
        try:
            return self.http().get(f"/orgs/{self._org}/repos", params={"per_page": self.config.page_size}).json() or []
        except HttpError:
            return []

    def get_metadata(self) -> dict[str, Any]:
        if not self._configured():
            return {"configured": False}
        repos = self._repos()
        return {"configured": True, "repository_count": len(repos)}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        if not self._configured():
            return []
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        for repo in self._repos():
            full = repo.get("full_name", "")
            name = repo.get("name", "")
            if "repositories" in wanted:
                items.append(EvidenceItem(
                    source_system="github", source_object_id=full, object_type="repository",
                    title=f"Repository {full}", content=repo.get("description") or full,
                    collected_timestamp=utcnow(), owner=(repo.get("owner") or {}).get("login", ""),
                    url=repo.get("html_url", ""), application=name,
                    metadata={"private": repo.get("private"), "default_branch": repo.get("default_branch")},
                ))
            if "pull_requests" in wanted:
                items.extend(self._pulls(full, name))
            if {"commits", "review_approvals"} & wanted:
                items.extend(self._commits(full, name))
            if "releases" in wanted:
                items.extend(self._releases(full, name))
            if "branch_protections" in wanted:
                bp = self._branch_protection(full, repo.get("default_branch", "main"))
                if bp is not None:
                    items.append(EvidenceItem(
                        source_system="github", source_object_id=f"{full}/protection",
                        object_type="branch_protection", title=f"Branch protection {full}",
                        content="enabled" if bp else "not configured", collected_timestamp=utcnow(),
                        application=name, control_mapping=["change-management", "code-review"],
                        framework_mapping=["SOC2-CC8"], metadata={"protected": bool(bp)},
                    ))
        return items

    def _pulls(self, full: str, name: str) -> list[EvidenceItem]:
        try:
            prs = self.http().get(f"/repos/{full}/pulls", params={"state": "all", "per_page": self.config.page_size}).json() or []
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for pr in prs:
            out.append(EvidenceItem(
                source_system="github", source_object_id=f"{full}#{pr.get('number')}",
                object_type="pull_request", title=pr.get("title", ""),
                content=(pr.get("body") or "")[:4000], collected_timestamp=utcnow(),
                owner=(pr.get("user") or {}).get("login", ""), url=pr.get("html_url", ""),
                application=name, control_mapping=["change-management", "code-review"],
                metadata={"state": pr.get("state"), "merged_at": pr.get("merged_at")},
            ))
        return out

    def _commits(self, full: str, name: str) -> list[EvidenceItem]:
        try:
            commits = self.http().get(f"/repos/{full}/commits", params={"per_page": self.config.page_size}).json() or []
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for c in commits:
            commit = c.get("commit", {}) or {}
            author = (commit.get("author") or {})
            out.append(EvidenceItem(
                source_system="github", source_object_id=f"{full}@{c.get('sha', '')[:12]}",
                object_type="commit", title=(commit.get("message", "") or "").splitlines()[0][:200],
                content=commit.get("message", "")[:4000], collected_timestamp=utcnow(),
                owner=author.get("name", "") or (c.get("author") or {}).get("login", ""),
                url=c.get("html_url", ""), application=name,
                control_mapping=["change-management", "code-review"], framework_mapping=["SOC2-CC8"],
                metadata={"sha": c.get("sha"), "date": author.get("date")},
            ))
        return out

    def _releases(self, full: str, name: str) -> list[EvidenceItem]:
        try:
            rels = self.http().get(f"/repos/{full}/releases", params={"per_page": self.config.page_size}).json() or []
        except HttpError:
            return []
        out: list[EvidenceItem] = []
        for r in rels:
            out.append(EvidenceItem(
                source_system="github", source_object_id=f"{full}/releases/{r.get('id')}",
                object_type="release", title=r.get("name") or r.get("tag_name", ""),
                content=(r.get("body") or "")[:4000], collected_timestamp=utcnow(),
                owner=(r.get("author") or {}).get("login", ""), url=r.get("html_url", ""),
                application=name, control_mapping=["release-management", "change-management"],
                framework_mapping=["SOC2-CC8"],
                metadata={"tag": r.get("tag_name"), "published_at": r.get("published_at"),
                          "draft": r.get("draft"), "prerelease": r.get("prerelease")},
            ))
        return out

    def _branch_protection(self, full: str, branch: str) -> bool | None:
        try:
            self.http().get(f"/repos/{full}/branches/{branch}/protection")
            return True
        except HttpError as exc:
            return False if exc.status == 404 else None
