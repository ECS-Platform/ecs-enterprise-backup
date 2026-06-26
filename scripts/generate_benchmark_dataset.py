"""Generate a deterministic synthetic benchmark dataset in the evidence repository."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from ecs_platform.repository import EvidenceRepository, RepositoryError

_APPLICATIONS = [
    "mobile-banking",
    "payments-gateway",
    "loan-origination",
    "corporate-banking",
    "treasury-ops",
    "retail-lending",
]
_SOURCES = ["jira", "jenkins", "sonarqube", "servicenow", "cmdb", "confluence", "github"]
_FRAMEWORKS = ["PCI-DSS", "SOC2", "ISO27001", "RBI-CSF", "AI-SDLC"]
_CONTROLS = ["access-control", "change-management", "vulnerability-management", "incident-response"]


def _build_item(idx: int) -> dict:
    app = _APPLICATIONS[idx % len(_APPLICATIONS)]
    src = _SOURCES[idx % len(_SOURCES)]
    fw = _FRAMEWORKS[idx % len(_FRAMEWORKS)]
    ctrl = _CONTROLS[idx % len(_CONTROLS)]
    uid = f"bench-{idx:04d}"
    now = datetime.now(timezone.utc).isoformat()
    title = f"Benchmark evidence {uid} for {app}"
    content = (
        f"Application {app} evidence from {src}. "
        f"Control focus {ctrl}. Framework relevance {fw}. "
        f"Observed timestamp {now}. Record {uid}."
    )
    return {
        "evidence_uid": uid,
        "source_system": src,
        "source_object_id": uid,
        "object_type": "document",
        "title": title,
        "content": content,
        "owner": "benchmark-runner",
        "url": f"https://ecs.local/benchmark/{uid}",
        "application": app,
        "control_mapping": [ctrl],
        "framework_mapping": [fw],
        "metadata": {"benchmark": True, "batch": "synthetic", "index": idx},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Create synthetic ECS benchmark evidence records.")
    parser.add_argument("--count", type=int, default=120, help="Number of synthetic evidence items.")
    args = parser.parse_args()

    items = [_build_item(i) for i in range(max(1, args.count))]
    try:
        with EvidenceRepository() as repo:
            written = repo.bulk_upsert(items)
    except RepositoryError as exc:
        print(f"dataset generation failed: {exc}")
        return 1
    print(f"dataset generation complete: {written} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
