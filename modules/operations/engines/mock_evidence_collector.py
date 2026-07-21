"""DEMO_MODE mock evidence collection from data/mock-evidence/<App>/<Framework>."""

from __future__ import annotations

import csv
import io
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.env_bootstrap import demo_mode_enabled
from modules.operations.engines.scheduler_progress import SchedulerProgressLog

_REPO_ROOT = Path(__file__).resolve().parents[3]
MOCK_EVIDENCE_ROOT = _REPO_ROOT / "data" / "mock-evidence"

MOCK_APP_DIRS: dict[str, str] = {
    "net banking": "NetBanking",
    "mobile banking": "MobileBanking",
    "payments": "Payments",
}

MOCK_FW_DIRS: dict[str, str] = {
    "pci dss": "PCI-DSS",
    "pci-dss": "PCI-DSS",
    "dpsc": "DPSC",
    "itpp": "ITPP",
    "csite": "C-SITE",
    "c-site": "C-SITE",
    "c site": "C-SITE",
    "vapt": "VAPT",
    "os baselining": "OS-Baseline",
    "db baselining": "DB-Baseline",
}

FRAMEWORK_CONTROL_HINTS: dict[str, dict[str, str]] = {
    "PCI-DSS": {"control_id": "PCI-8.3", "control_name": "MFA for privileged access"},
    "DPSC": {"control_id": "DPSC-4.1", "control_name": "Consent and data retention"},
    "ITPP": {"control_id": "IT-C-03", "control_name": "Backup verification"},
    "C-SITE": {"control_id": "CS-C-03", "control_name": "SOC integration readiness"},
    "OS-Baseline": {"control_id": "OSB-14", "control_name": "CIS hardening baseline"},
    "DB-Baseline": {"control_id": "DB-C-01", "control_name": "Database access control"},
    "VAPT": {"control_id": "VAPT-9", "control_name": "External pentest remediation"},
}

APP_DISPLAY: dict[str, str] = {
    "NetBanking": "Net Banking",
    "MobileBanking": "Mobile Banking",
    "Payments": "Payments",
}


@dataclass
class MockCollectionSummary:
    run_id: str = ""
    applications: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    sources_executed: int = 0
    files_discovered: int = 0
    new_evidence: int = 0
    duplicates_skipped: int = 0
    versions_created: int = 0
    failures: int = 0
    postgresql_count: int = 0
    object_storage_count: int = 0
    pgvector_count: int = 0
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "applications": self.applications,
            "frameworks": self.frameworks,
            "sources_executed": self.sources_executed,
            "files_discovered": self.files_discovered,
            "new_evidence": self.new_evidence,
            "duplicates_skipped": self.duplicates_skipped,
            "versions_created": self.versions_created,
            "failures": self.failures,
            "postgresql_count": self.postgresql_count,
            "object_storage_count": self.object_storage_count,
            "pgvector_count": self.pgvector_count,
            "receipts": self.receipts,
        }


def _norm(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def mock_evidence_root() -> Path:
    override = os.environ.get("ECS_MOCK_EVIDENCE_ROOT", "").strip()
    return Path(override) if override else MOCK_EVIDENCE_ROOT


def map_application_folder(label: str) -> str | None:
    return MOCK_APP_DIRS.get(_norm(label))


def map_framework_folder(label: str) -> str | None:
    return MOCK_FW_DIRS.get(_norm(label))


def selected_mock_combinations(applications: list[str], frameworks: list[str]) -> list[tuple[str, str, Path]]:
    """Return (app_label, fw_label, folder_path) for selected UI labels."""
    apps = applications or list(APP_DISPLAY.values())
    fws = frameworks or list(MOCK_FW_DIRS.keys())
    app_dirs = {map_application_folder(a) for a in apps if map_application_folder(a)}
    fw_dirs = {map_framework_folder(f) for f in fws if map_framework_folder(f)}
    if not app_dirs:
        app_dirs = set(APP_DISPLAY.keys())
    if not fw_dirs:
        fw_dirs = set(FRAMEWORK_CONTROL_HINTS.keys())
    combos: list[tuple[str, str, Path]] = []
    root = mock_evidence_root()
    for app_dir in sorted(app_dirs):
        for fw_dir in sorted(fw_dirs):
            folder = root / app_dir / fw_dir
            if folder.is_dir():
                combos.append((APP_DISPLAY.get(app_dir, app_dir), fw_dir.replace("-", " "), folder))
    return combos


def _artifact_content(app_dir: str, fw_dir: str, *, ext: str) -> tuple[str, bytes, str]:
    hint = FRAMEWORK_CONTROL_HINTS.get(fw_dir, {"control_id": "CTRL-001", "control_name": "Control"})
    app_name = APP_DISPLAY.get(app_dir, app_dir)
    if ext == "json":
        payload = {
            "application": app_name,
            "environment": "UAT",
            "framework": fw_dir.replace("-", " "),
            "control_id": hint["control_id"],
            "control_name": hint["control_name"],
            "status": "collected",
            "source": "mock_evidence",
            "summary": f"Mock scheduler evidence for {app_name} / {fw_dir}",
        }
        text = json.dumps(payload, indent=2, sort_keys=True)
        return f"mock_{fw_dir.lower()}_{app_dir.lower()}.json", text.encode("utf-8"), "application/json"
    if ext == "txt":
        text = (
            f"ECS Mock Evidence\nApplication: {app_name}\nFramework: {fw_dir}\n"
            f"Control: {hint['control_id']} — {hint['control_name']}\nEnvironment: UAT\n"
        )
        return f"mock_{fw_dir.lower()}_{app_dir.lower()}.txt", text.encode("utf-8"), "text/plain"
    if ext == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["application", "framework", "control_id", "status"])
        writer.writerow([app_name, fw_dir, hint["control_id"], "pass"])
        text = buf.getvalue()
        return f"mock_{fw_dir.lower()}_{app_dir.lower()}.csv", text.encode("utf-8"), "text/csv"
    text = f"%PDF-1.4\n% Mock PDF evidence placeholder for {app_name} / {fw_dir}\n"
    return f"mock_{fw_dir.lower()}_{app_dir.lower()}.pdf", text.encode("utf-8"), "application/pdf"


def ensure_mock_evidence_tree() -> int:
    """Create mock-evidence folders/artifacts only where missing. Returns folders ensured."""
    if not demo_mode_enabled() and not os.environ.get("ECS_MOCK_EVIDENCE_FORCE_INIT"):
        return 0
    root = mock_evidence_root()
    exts = ["json", "txt", "csv", "pdf"]
    ensured = 0
    idx = 0
    for app_dir in APP_DISPLAY:
        for fw_dir in FRAMEWORK_CONTROL_HINTS:
            folder = root / app_dir / fw_dir
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
            manifest_path = folder / "manifest.json"
            ext = exts[idx % len(exts)]
            idx += 1
            filename, content, mime = _artifact_content(app_dir, fw_dir, ext=ext)
            artifact_path = folder / filename
            hint = FRAMEWORK_CONTROL_HINTS[fw_dir]
            if not manifest_path.exists():
                manifest_path.write_text(
                    json.dumps(
                        {
                            "application": APP_DISPLAY[app_dir],
                            "environment": "UAT",
                            "framework": fw_dir.replace("-", " "),
                            "control_id": hint["control_id"],
                            "control_name": hint["control_name"],
                            "evidence_file": filename,
                            "source_connector": "mock_evidence",
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            if not artifact_path.exists():
                artifact_path.write_bytes(content)
            ensured += 1
    return ensured


def _count_persistence() -> tuple[int, int, int]:
    pg = 0
    objects = 0
    vectors = 0
    try:
        from modules.operations.engines import evidence_repository as ops_repo

        pg = len(ops_repo.evidence_repository)
        objects = sum(1 for r in ops_repo.evidence_repository if r.get("object_uri") or (r.get("metadata") or {}).get("object_key"))
        vectors = sum(
            1 for r in ops_repo.evidence_repository
            if (r.get("search_index") or {}).get("indexed") or (r.get("metadata") or {}).get("pgvector_indexed")
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from ecs_platform.rag import rag_status

        status = rag_status()
        if status.get("vector_count"):
            vectors = max(vectors, int(status["vector_count"]))
        if status.get("evidence_count"):
            pg = max(pg, int(status["evidence_count"]))
    except Exception:  # noqa: BLE001
        pass
    return pg, objects, vectors


def collect_mock_evidence(
    *,
    user: str,
    run_id: str,
    applications: list[str],
    frameworks: list[str],
    progress: SchedulerProgressLog,
    dry_run: bool = False,
) -> MockCollectionSummary:
    """Collect mock evidence for selected app/framework combinations (DEMO_MODE only)."""
    summary = MockCollectionSummary(
        run_id=run_id,
        applications=list(applications or []),
        frameworks=list(frameworks or []),
    )
    if not demo_mode_enabled():
        progress.append("mock collection", "Skipped", detail="Not DEMO_MODE")
        return summary

    ensure_mock_evidence_tree()
    progress.append("plan built", "Completed", detail=f"run_id={run_id}")
    progress.append("source scanned", "Running", detail=str(mock_evidence_root()))
    combos = selected_mock_combinations(applications, frameworks)
    progress.append("source scanned", "Completed", detail=f"combinations={len(combos)}")
    summary.sources_executed = len(combos)

    from modules.operations.engines.evidence_repository import find_upload_by_sha256, register_upload

    for app_label, fw_label, folder in combos:
        manifest_path = folder / "manifest.json"
        if not manifest_path.is_file():
            progress.append("file discovered", "Failed", detail=f"missing manifest in {folder.name}")
            summary.failures += 1
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        evidence_file = folder / str(manifest.get("evidence_file") or "evidence.json")
        if not evidence_file.is_file():
            alt = next((p for p in folder.iterdir() if p.is_file() and p.name != "manifest.json"), None)
            evidence_file = alt or evidence_file
        if not evidence_file.is_file():
            progress.append("file discovered", "Failed", detail=f"no artifact in {folder}")
            summary.failures += 1
            continue

        summary.files_discovered += 1
        progress.append(
            "file discovered",
            "Completed",
            detail=f"{app_label}/{fw_label} -> {evidence_file.name}",
        )
        content = evidence_file.read_bytes()
        content_hash = __import__("hashlib").sha256(content).hexdigest()
        progress.append("hash checked", "Completed", detail=f"sha256={content_hash[:12]}…")

        existing = find_upload_by_sha256(content_hash)
        if existing is not None:
            progress.append("duplicate skipped", "Skipped", detail=f"existing={existing.get('evidence_id')}")
            summary.duplicates_skipped += 1
            summary.receipts.append(
                {
                    "application": app_label,
                    "framework": manifest.get("framework") or fw_label,
                    "evidence_id": existing.get("evidence_id"),
                    "duplicate": True,
                    "sha256": content_hash,
                    "run_id": run_id,
                }
            )
            continue

        if dry_run:
            progress.append("metadata stored", "Skipped", detail="dry-run")
            progress.append("object stored", "Skipped", detail="dry-run")
            progress.append("version/workflow created", "Skipped", detail="dry-run")
            progress.append("PGVector indexed", "Skipped", detail="dry-run")
            continue

        progress.append("duplicate accepted", "Completed", detail=evidence_file.name)
        framework = str(manifest.get("framework") or fw_label)
        control_id = str(manifest.get("control_id") or "CTRL-001")
        meta = {
            "scheduler_run_id": run_id,
            "collection_source": "mock_evidence",
            "environment": str(manifest.get("environment") or "UAT"),
            "framework": framework,
            "control_name": str(manifest.get("control_name") or control_id),
            "object_key": f"mock-evidence/{folder.relative_to(mock_evidence_root())}/{evidence_file.name}".replace("\\", "/"),
            "content_sha256": content_hash,
            "duplicate": False,
        }
        mime = "application/json" if evidence_file.suffix.lower() == ".json" else (
            "text/csv" if evidence_file.suffix.lower() == ".csv" else (
                "application/pdf" if evidence_file.suffix.lower() == ".pdf" else "text/plain"
            )
        )
        try:
            record = register_upload(
                filename=evidence_file.name,
                content=content,
                uploaded_by=user or "scheduler",
                framework=framework.replace("-", " ") if "-" in framework else framework,
                application=str(manifest.get("application") or app_label),
                control=control_id,
                source_connector="mock_evidence",
                source_item_id=f"mock-evidence/{folder.name}/{evidence_file.name}",
                source_url=f"object://{meta['object_key']}",
                environment=str(manifest.get("environment") or "UAT"),
                mime_type=mime,
                metadata=meta,
                custody_mode=os.environ.get("ECS_MOCK_EVIDENCE_CUSTODY", "SNAPSHOT"),
            )
            index_report = record.get("search_index") or {}
            meta["pgvector_indexed"] = bool(index_report.get("indexed"))
            progress.append("metadata stored", "Completed", detail=record.get("evidence_id", ""))
            progress.append("object stored", "Completed", detail=meta["object_key"])
            progress.append("version/workflow created", "Completed", detail=f"v{record.get('version', 1)}")
            if index_report.get("indexed"):
                progress.append("PGVector indexed", "Completed", detail=record.get("evidence_id", ""))
            else:
                progress.append(
                    "PGVector indexed",
                    "Skipped",
                    detail=str(index_report.get("reason") or "index_not_required"),
                )
            summary.new_evidence += 1
            summary.versions_created += 1
            summary.postgresql_count += 1
            if record.get("object_uri") or meta.get("object_key"):
                summary.object_storage_count += 1
            if index_report.get("indexed"):
                summary.pgvector_count += 1
            summary.receipts.append(
                {
                    "application": app_label,
                    "framework": framework,
                    "evidence_id": record.get("evidence_id"),
                    "duplicate": False,
                    "sha256": content_hash,
                    "version": record.get("version", 1),
                    "run_id": run_id,
                    "workflow_status": record.get("status", "Uploaded"),
                    "pgvector_indexed": meta["pgvector_indexed"],
                }
            )
            from modules.shared.services.evidence_workflow_engine import enroll_collected_evidence

            enroll_collected_evidence(record, source_type="mock_evidence")
        except Exception as exc:  # noqa: BLE001
            progress.append("metadata stored", "Failed", detail=str(exc))
            summary.failures += 1

    progress.append("completed", "Completed", detail=f"new={summary.new_evidence} dup={summary.duplicates_skipped}")
    return summary
