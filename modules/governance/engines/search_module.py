"""Enterprise evidence discovery — not workflow queues."""

from app import ecs_state
from modules.operations.engines.evidence_repository import evidence_repository
from modules.frameworks.engines.framework_catalog import FRAMEWORK_CATALOG, get_all_evidence_records
from modules.operations.engines.evidence_repository import get_reuse_graph


def search_evidences(
    q: str = "",
    framework: str = "",
    application: str = "",
    owner: str = "",
    status: str = "",
):
    results = []
    catalog = get_all_evidence_records()

    for ev in catalog:
        item = {
            "type": "catalog",
            "framework": ev.get("framework", ""),
            "control": ev.get("control_name", ev.get("control", "")),
            "evidence": ev.get("evidence_name", ""),
            "application": ev.get("application_name", ""),
            "owner": ev.get("uploaded_by", "Enterprise Owner"),
            "status": ev.get("audit_status", "Pending"),
            "lifecycle": ev.get("evidence_status", "Current"),
            "evidence_id": ev.get("evidence_id", ""),
            "semantic_score": _semantic_score(q, ev) if q else 0,
        }
        results.append(item)

    for r in evidence_repository:
        results.append(
            {
                "type": "upload",
                "framework": ", ".join(r["framework_tags"]),
                "control": r.get("control", ""),
                "evidence": r["filename"],
                "application": ", ".join(r["application_tags"]),
                "owner": r["uploaded_by"],
                "status": r["status"],
                "lifecycle": r["lifecycle"],
                "evidence_id": r["evidence_id"],
                "semantic_score": _semantic_score(q, r) if q else 0,
            }
        )

    if q:
        ql = q.lower()
        results = [
            r
            for r in results
            if ql in r["framework"].lower()
            or ql in r["control"].lower()
            or ql in r["evidence"].lower()
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
        "framework_filters": list(FRAMEWORK_CATALOG.keys()),
        "total_indexed": len(get_all_evidence_records()) + len(evidence_repository),
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
    return mapping.get(framework, list(FRAMEWORK_CATALOG.keys())[:2])
