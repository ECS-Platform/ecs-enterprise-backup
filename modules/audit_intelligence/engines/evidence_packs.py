"""Evidence Packs (Milestone 3).

Assemble audit-ready evidence packs from the Evidence Repository, each with a
deterministic **JSON manifest** carrying metadata, per-item hashes/checksums, and a
pack-level content hash (a hash over the sorted item hashes — stable and
verifiable).

Pack types:
  * evidence pack     — an explicit set of evidence keys.
  * framework pack     — all latest evidence for a framework.
  * application pack   — all latest evidence for an application's assets.
  * asset pack         — all latest evidence for one asset.

Manifests are pure metadata (no credentials/secrets) and are safe to export.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.models import EvidenceArtifact


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pack_hash(items: list[EvidenceArtifact]) -> str:
    """Deterministic hash over the sorted per-item content hashes."""
    joined = "|".join(sorted(a.content_hash for a in items))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _manifest(
    *,
    pack_type: str,
    pack_scope: str,
    items: list[EvidenceArtifact],
) -> dict[str, Any]:
    verdicts: dict[str, int] = {}
    frameworks: set[str] = set()
    technologies: set[str] = set()
    for a in items:
        verdicts[a.verdict or "Unassessed"] = verdicts.get(a.verdict or "Unassessed", 0) + 1
        frameworks.update(a.frameworks)
        if a.technology:
            technologies.add(a.technology)
    pack_hash = _pack_hash(items)
    return {
        "pack_type": pack_type,
        "pack_scope": pack_scope,
        "generated_at": _now(),
        "item_count": len(items),
        "pack_hash": pack_hash,
        "pack_checksum": pack_hash[:8],
        "technologies": sorted(technologies),
        "frameworks": sorted(frameworks),
        "verdict_summary": verdicts,
        "items": [
            {
                "evidence_key": a.evidence_key,
                "version": a.version,
                "control_id": a.control_id,
                "technology": a.technology,
                "asset_id": a.asset_id,
                "frameworks": list(a.frameworks),
                "verdict": a.verdict,
                "control_status": a.control_status,
                "content_hash": a.content_hash,
                "checksum": a.checksum,
                "size_bytes": a.size_bytes,
                "collected_at": a.collected_at,
                "filename": a.filename,
            }
            for a in sorted(items, key=lambda x: (x.asset_id, x.control_id))
        ],
    }


def verify_manifest(manifest: dict[str, Any]) -> bool:
    """Recompute the pack hash from the manifest's item hashes and compare."""
    joined = "|".join(sorted(i["content_hash"] for i in manifest.get("items", [])))
    recomputed = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return recomputed == manifest.get("pack_hash")


def manifest_json(manifest: dict[str, Any]) -> str:
    """Serialize a manifest to canonical (sorted-key) JSON."""
    return json.dumps(manifest, indent=2, sort_keys=True, default=str)


# --------------------------------------------------------------------------- #
# Pack builders
# --------------------------------------------------------------------------- #
def evidence_pack(evidence_keys: list[str]) -> dict[str, Any]:
    """Pack for an explicit set of evidence keys (latest version of each)."""
    items = [a for k in evidence_keys if (a := repo.get_latest(k)) is not None]
    return _manifest(pack_type="evidence", pack_scope=",".join(evidence_keys), items=items)


def framework_pack(framework: str) -> dict[str, Any]:
    """Pack of all latest evidence tagged with a framework."""
    items = repo.search(framework=framework, latest_only=True)
    return _manifest(pack_type="framework", pack_scope=framework, items=items)


def asset_pack(asset_id: str) -> dict[str, Any]:
    """Pack of all latest evidence for one asset."""
    items = repo.search(asset_id=asset_id, latest_only=True)
    return _manifest(pack_type="asset", pack_scope=asset_id, items=items)


def application_pack(application: str, asset_ids: list[str]) -> dict[str, Any]:
    """Pack of all latest evidence for an application's assets.

    Applications are not yet persisted with a first-class asset linkage, so callers
    pass the application's ``asset_ids`` explicitly (documented assumption). All
    latest evidence for those assets is aggregated.
    """
    items: list[EvidenceArtifact] = []
    for aid in asset_ids:
        items.extend(repo.search(asset_id=aid, latest_only=True))
    return _manifest(pack_type="application", pack_scope=application, items=items)


def technology_pack(technology: str) -> dict[str, Any]:
    """Pack of all latest evidence for a technology (bonus convenience)."""
    items = repo.search(technology=technology, latest_only=True)
    return _manifest(pack_type="technology", pack_scope=technology, items=items)
