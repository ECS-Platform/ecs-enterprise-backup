"""Evidence repository: bulk upload, metadata, hashes, lifecycle, reuse."""

import hashlib
import re
from datetime import datetime, timezone

from app import ecs_state

evidence_repository = []
upload_tracker = []
evidence_reuse_map = {}
_evidence_counter = 0


def _next_id():
    global _evidence_counter
    _evidence_counter += 1
    return f"EVD-{_evidence_counter:05d}"


def enforce_naming(filename: str, framework: str, application: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    prefix = re.sub(r"\s+", "_", framework.upper())[:12]
    app = re.sub(r"\s+", "_", application.upper())[:10]
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    if base.lower().startswith(f"{prefix.lower()}_"):
        return base
    return f"{prefix}_{app}_{ts}_{base}"


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def integrity_check(stored_hash: str, content: bytes) -> dict:
    current = compute_hash(content) if content else stored_hash
    ok = current == stored_hash
    return {
        "stored_hash": stored_hash,
        "current_hash": current,
        "valid": ok,
        "status": "Valid" if ok else "Tamper Detected (simulated)",
    }


def register_upload(
    filename: str,
    content: bytes,
    uploaded_by: str,
    framework: str = "",
    application: str = "Net Banking",
    control: str = "",
):
    std_name = enforce_naming(filename, framework or "GENERAL", application)
    file_hash = compute_hash(content or std_name.encode())
    integrity = integrity_check(file_hash, content or b"")
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "evidence_id": _next_id(),
        "filename": std_name,
        "original_filename": filename,
        "framework_tags": [framework] if framework else ["Cross-Framework"],
        "application_tags": [application],
        "control": control,
        "uploaded_by": uploaded_by,
        "uploaded_at": now,
        "sha256": file_hash,
        "integrity": integrity["status"],
        "integrity_valid": integrity["valid"],
        "lifecycle": "Draft",
        "summary": "",
        "size_bytes": len(content) if content else 0,
        "status": "Uploaded",
    }
    record["summary"] = generate_summary(record)
    record["version"] = 1
    record["reviewer"] = "Pending Assignment"
    evidence_repository.append(record)
    from modules.shared.services.audit_trail import log_event, record_version

    record_version(record["evidence_id"], std_name, 1, uploaded_by)
    log_event(
        "Evidence Uploaded",
        uploaded_by,
        framework or "Cross-Framework",
        control,
        std_name,
        record["evidence_id"],
    )
    upload_tracker.append(
        {
            "evidence_id": record["evidence_id"],
            "filename": std_name,
            "status": "Complete",
            "uploaded_by": uploaded_by,
            "at": now,
        }
    )
    _link_reuse(record)
    return record


def _link_reuse(record):
    """Simulate vector embedding reuse across controls."""
    key = record["filename"].lower()
    if key in evidence_reuse_map:
        evidence_reuse_map[key]["linked_controls"].append(
            {
                "framework": record["framework_tags"][0],
                "control": record.get("control") or "Shared Control",
            }
        )
        record["reused"] = True
        record["reuse_group"] = evidence_reuse_map[key]["group_id"]
    else:
        group_id = f"REUSE-{len(evidence_reuse_map) + 1:03d}"
        evidence_reuse_map[key] = {
            "group_id": group_id,
            "filename": record["filename"],
            "linked_controls": [
                {
                    "framework": record["framework_tags"][0],
                    "control": record.get("control") or "Primary",
                }
            ],
        }
        if record["framework_tags"][0] != "Cross-Framework":
            evidence_reuse_map[key]["linked_controls"].append(
                {"framework": "DPSC", "control": "Log Monitoring"}
            )
            evidence_reuse_map[key]["linked_controls"].append(
                {"framework": "CSITE", "control": "SIEM Alerts"}
            )
        record["reuse_group"] = group_id
        record["reused"] = False


def refresh_repository_from_frameworks(source: str = "scheduler"):
    from modules.frameworks.engines.framework_catalog import get_all_evidence_records

    added = 0
    for row in get_all_evidence_records():
        exists = any(r.get("evidence_id") == row["evidence_id"] for r in evidence_repository)
        if exists:
            continue
        content = f"{row['framework']}|{row['control']}|{row['evidence_name']}|{source}".encode()
        register_upload(
            filename=row["mock_file"],
            content=content,
            uploaded_by=row["uploaded_by"] if source == "startup" else f"Scheduler ({source})",
            framework=row["framework"],
            application=row["application_name"],
            control=row["control"],
        )
        if evidence_repository:
            evidence_repository[-1]["evidence_status"] = row.get("evidence_status", "Current")
            evidence_repository[-1]["audit_status"] = row.get("audit_status", "Pending")
            evidence_repository[-1]["reviewer"] = row.get("reviewer", "")
            evidence_repository[-1]["comments"] = row.get("comments", "")
            evidence_repository[-1]["expiry_date"] = row.get("expiry_date", "")
            evidence_repository[-1]["server_name"] = row.get("server_name", "")
        added += 1
    return added


def _guess_application(framework: str, control: str) -> str:
    for item in ecs_state.PCI_DSS_MOCK_EVIDENCES:
        if item["control"] == control:
            return item["application"]
    for row in ecs_state.scheduler_data:
        if len(row) >= 2 and row[1] == framework:
            return row[0]
    return "Net Banking"


def generate_summary(record: dict) -> str:
    fw = ", ".join(record["framework_tags"])
    app = ", ".join(record["application_tags"])
    return (
        f"AI Summary: {record['filename']} supports {fw} for {app}. "
        f"Integrity {record['integrity']}. Uploaded by {record['uploaded_by']}."
    )


def get_health_dashboard():
    from modules.executive_overview.engines.demo_metrics import HEALTH_METRICS

    rows = []
    for r in evidence_repository:
        rows.append(
            {
                "evidence_id": r["evidence_id"],
                "filename": r["filename"],
                "sha256": r["sha256"][:16] + "...",
                "full_hash": r["sha256"],
                "integrity": r["integrity"],
                "valid": r["integrity_valid"],
                "framework": ", ".join(r["framework_tags"]),
            }
        )
    valid = sum(1 for r in rows if r["valid"])
    total = max(len(rows), HEALTH_METRICS["total_artifacts"] // 100)
    if not rows:
        total = HEALTH_METRICS["total_artifacts"]
        valid = int(total * HEALTH_METRICS["valid_integrity_pct"] / 100)
    return {
        "rows": rows,
        "total": total if rows else HEALTH_METRICS["total_artifacts"],
        "valid_count": valid if rows else int(HEALTH_METRICS["total_artifacts"] * 0.987),
        "tamper_count": HEALTH_METRICS["tamper_alerts"] if not rows else len(rows) - valid,
        "overdue_count": HEALTH_METRICS["overdue_count"],
        "stale_count": HEALTH_METRICS["stale_count"],
        "valid_pct": HEALTH_METRICS["valid_integrity_pct"],
    }


def get_reuse_graph():
    nodes = []
    edges = []
    for key, info in evidence_reuse_map.items():
        nodes.append({"id": info["group_id"], "label": info["filename"][:30]})
        for i, link in enumerate(info["linked_controls"]):
            target = f"{link['framework']}::{link['control']}"
            edges.append({"from": info["group_id"], "to": target, "label": link["framework"]})
    groups = list(evidence_reuse_map.values())
    if not groups:
        groups = [
            {
                "group_id": "REUSE-001",
                "filename": "PCI_DSS_NETBANKING_20260524_db_tde_report.pdf",
                "linked_controls": [
                    {"framework": "PCI DSS", "control": "Req 3.4 — Encryption at Rest"},
                    {"framework": "DPSC", "control": "Log Monitoring"},
                    {"framework": "DB Baselining", "control": "DB Encryption"},
                ],
            },
            {
                "group_id": "REUSE-002",
                "filename": "CSITE_SIEM_alert_export.csv",
                "linked_controls": [
                    {"framework": "CSITE", "control": "SIEM Alerts"},
                    {"framework": "PCI DSS", "control": "Req 10.6 — Log Review"},
                ],
            },
        ]
    return {"nodes": nodes, "edges": edges, "groups": groups}


def where_else_used(filename: str) -> str:
    key = filename.lower()
    for k, info in evidence_reuse_map.items():
        if k in key or filename.lower() in k:
            links = info["linked_controls"]
            parts = [f"{l['framework']} / {l['control']}" for l in links]
            return "Also used in: " + " | ".join(parts)
    return "No reuse mapping found for that evidence (upload or scheduler pull first)."


def get_summaries():
    return [
        {
            "evidence_id": r["evidence_id"],
            "filename": r["filename"],
            "summary": r["summary"],
            "framework": ", ".join(r["framework_tags"]),
        }
        for r in evidence_repository[-20:]
    ]
