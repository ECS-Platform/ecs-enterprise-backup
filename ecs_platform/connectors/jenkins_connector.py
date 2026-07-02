"""Jenkins connector (self-hosted) — real connectivity via the JSON REST API.

Auth: basic (user + API token). Collects jobs, recent builds, and test results.
"""

from __future__ import annotations

import time
from typing import Any, Iterable

from ecs_platform.connectors.base import BaseConnector, ConnectorHealth, EvidenceItem, utcnow
from ecs_platform.connectors.http_client import HttpClient, HttpError


class JenkinsConnector(BaseConnector):
    DEFAULT_TYPES = ["jobs", "builds", "test_results"]

    def _apply_auth(self, client: HttpClient) -> None:
        user = self.config.secret("username_env")
        token = self.config.secret("password_env")
        if user or token:
            client.with_basic(user, token)

    def test_connection(self) -> ConnectorHealth:
        if not self.config.enabled or not self.config.base_url:
            return self._disabled_health()
        start = time.time()
        try:
            resp = self.http().get("/api/json", params={"tree": "jobs[name]"})
            latency = int((time.time() - start) * 1000)
            authed = resp.status == 200
            count = len((resp.json() or {}).get("jobs", []))
            return self._health(connected=resp.status == 200, authenticated=authed,
                                latency_ms=latency, detail=f"{count} jobs visible")
        except HttpError as exc:
            return self._health(connected=False, authenticated=False, detail=str(exc))

    def _jobs(self) -> list[dict[str, Any]]:
        try:
            resp = self.http().get("/api/json", params={"tree": "jobs[name,url,color,lastBuild[number,url]]"})
            return (resp.json() or {}).get("jobs", [])
        except HttpError:
            return []

    def get_metadata(self) -> dict[str, Any]:
        jobs = self._jobs()
        return {"job_count": len(jobs), "jobs": [j.get("name") for j in jobs]}

    def collect_evidence(self, object_types: Iterable[str] | None = None) -> list[EvidenceItem]:
        wanted = set(object_types or self.config.collect or self.DEFAULT_TYPES)
        items: list[EvidenceItem] = []
        for job in self._jobs():
            name = job.get("name", "")
            if "jobs" in wanted:
                items.append(EvidenceItem(
                    source_system="jenkins", source_object_id=name, object_type="ci_job",
                    title=f"CI job {name}", content=f"Pipeline {name} (status {job.get('color')})",
                    collected_timestamp=utcnow(), application=name, url=job.get("url", ""),
                    control_mapping=["ci-cd", "change-management"], framework_mapping=["SOC2-CC8"],
                ))
            if {"builds", "test_results"} & wanted:
                items.extend(self._builds(job, wanted))
        return items

    def _builds(self, job: dict[str, Any], wanted: set[str]) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        name = job.get("name", "")
        try:
            resp = self.http().get(f"/job/{name}/api/json",
                                   params={"tree": "builds[number,result,timestamp,url]{0,10}"})
        except HttpError:
            return out
        for build in (resp.json() or {}).get("builds", []):
            num = build.get("number")
            if "builds" in wanted:
                out.append(EvidenceItem(
                    source_system="jenkins", source_object_id=f"{name}#{num}", object_type="ci_build",
                    title=f"Build {name} #{num}", content=f"Result {build.get('result')}",
                    collected_timestamp=utcnow(), application=name, url=build.get("url", ""),
                    control_mapping=["ci-cd"], metadata={"result": build.get("result")},
                ))
            if "test_results" in wanted:
                tr = self._test_report(name, num)
                if tr:
                    out.append(EvidenceItem(
                        source_system="jenkins", source_object_id=f"{name}#{num}/tests",
                        object_type="test_result", title=f"Tests {name} #{num}",
                        content=f"pass={tr.get('passCount')} fail={tr.get('failCount')} skip={tr.get('skipCount')}",
                        collected_timestamp=utcnow(), application=name,
                        control_mapping=["secure-sdlc", "testing"], metadata=tr,
                    ))
        return out

    def _test_report(self, name: str, num: Any) -> dict[str, Any]:
        try:
            resp = self.http().get(f"/job/{name}/{num}/testReport/api/json",
                                   params={"tree": "passCount,failCount,skipCount"})
            return resp.json() or {}
        except HttpError:
            return {}
