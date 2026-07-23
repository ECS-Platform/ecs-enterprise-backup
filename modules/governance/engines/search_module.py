"""Enterprise evidence discovery — not workflow queues."""

from modules.shared.services.evidence_authoritative_reader import (
    collect_authoritative_evidence_rows,
)
from modules.operations.engines.evidence_repository import get_reuse_graph


def search_evidences(
    q: str = "",
    framework: str = "",
    application: str = "",
    owner: str = "",
    status: str = "",
):
    results = []
    for rec in collect_authoritative_evidence_rows():
        item = {
            "type": "persisted",
            "framework": str(rec.get("framework") or ""),
            "control": str(rec.get("control_id") or rec.get("control") or ""),
            "evidence": str(rec.get("filename") or rec.get("evidence_id") or ""),
            "original_filename": str(rec.get("original_filename") or (rec.get("metadata") or {}).get("original_filename") or ""),
            "application": str(rec.get("application") or ""),
            "owner": str(rec.get("uploaded_by") or "Enterprise Owner"),
            "status": str(rec.get("audit_status") or rec.get("workflow_status") or rec.get("status") or ""),
            "lifecycle": str(rec.get("lifecycle") or "Collected"),
            "evidence_id": str(rec.get("evidence_id") or ""),
            "sha256": str(rec.get("sha256") or ""),
            "version": int(rec.get("version") or 1),
            "custody_mode": str(rec.get("custody_mode") or ""),
            "object_reference": str(rec.get("object_reference") or rec.get("object_uri") or ""),
            "collection_source": str(rec.get("collection_source") or ""),
            "collected_at": str(rec.get("collected_at") or ""),
            "semantic_score": _semantic_score(q, rec) if q else 0,
        }
        results.append(item)

    if q:
        ql = q.lower()
        results = [
            r
            for r in results
            if ql in r["framework"].lower()
            or ql in r["control"].lower()
            or ql in r["evidence"].lower()
            or ql in str(r.get("original_filename", "")).lower()
            or ql in r["application"].lower()
            or r.get("semantic_score", 0) >= 40
        ]
        results.sort(key=lambda x: x.get("semantic_score", 0), reverse=True)
    if framework:
        results = [r for r in results if framework.lower() in r["framework"].lower()]
    if application:
        results = [r for r in results if application.lower() in r["application"].lower()]
    if owner:
        results = [r for r in results if owner.lower() in r["owner"].lower()]
    if status:
        results = [r for r in results if status.lower() in r["status"].lower()]

    return results


def build_search_discovery(
    q: str = "",
    framework: str = "",
    application: str = "",
    owner: str = "",
    status: str = "",
) -> dict:
    results = search_evidences(q, framework, application, owner, status)
    reuse_graph = get_reuse_graph()
    reuse_suggestions = []
    for g in reuse_graph.get("groups", [])[:8]:
        reuse_suggestions.append({
            "group_id": g["group_id"],
            "filename": g["filename"],
            "frameworks": list({l["framework"] for l in g["linked_controls"]}),
            "controls_count": len(g["linked_controls"]),
            "savings_hours": (len(g["linked_controls"]) - 1) * 4,
        })

    semantic_matches = []
    for r in results[:12]:
        if r.get("semantic_score", 0) >= 30 or not q:
            semantic_matches.append({
                **r,
                "match_type": "Semantic" if r.get("semantic_score", 0) >= 60 else "Keyword",
                "related_frameworks": _related_frameworks(r.get("framework", "")),
            })

    related = []
    if results:
        seed = results[0]
        for r in results[1:6]:
            if r["framework"] == seed["framework"] or r["application"] == seed["application"]:
                related.append(r)

    return {
        "results": results[:25],
        "semantic_matches": semantic_matches[:10] if q else results[:10],
        "reuse_suggestions": reuse_suggestions,
        "related_evidences": related,
        "framework_filters": sorted({r.get("framework", "") for r in results if r.get("framework")}),
        "total_indexed": len(collect_authoritative_evidence_rows()),
    }


def _semantic_score(q: str, record: dict) -> int:
    if not q:
        return 0
    ql = q.lower()
    score = 0
    fields = [
        record.get("evidence_name", record.get("evidence", "")),
        record.get("control_name", record.get("control", "")),
        record.get("framework", ""),
        record.get("application_name", record.get("application", "")),
        record.get("filename", ""),
    ]
    for f in fields:
        fl = str(f).lower()
        if ql in fl:
            score += 70 if fl.startswith(ql) else 45
        elif any(w in fl for w in ql.split() if len(w) > 2):
            score += 25
    return min(score, 99)


def _related_frameworks(framework: str) -> list[str]:
    mapping = {
        "PCI DSS": ["DPSC", "CSITE"],
        "DPSC": ["PCI DSS", "OS Baselining"],
        "OS Baselining": ["DB Baselining", "Nginx Baselining"],
        "DB Baselining": ["OS Baselining", "PCI DSS"],
        "Nginx Baselining": ["OS Baselining", "CSITE"],
        "CSITE": ["PCI DSS", "DPSC"],
    }
    return mapping.get(framework, ["PCI DSS", "DPSC"])
