"""Repository / observation / packs service facade (Milestone 3).

Serialization-friendly layer over the observation, evidence-repository, and packs
engines for future REST/UI layers.
"""

from __future__ import annotations

from typing import Any

from modules.audit_intelligence.engines import evidence_packs as packs
from modules.audit_intelligence.engines import evidence_repository as repo
from modules.audit_intelligence.engines import observation_generation as obs


# --------------------------------------------------------------------------- #
# Observations
# --------------------------------------------------------------------------- #
def list_observations(**filters: str) -> list[dict[str, Any]]:
    return [o.to_dict() for o in obs.list_observations(**filters)]


def get_observation(obs_id: str) -> dict[str, Any] | None:
    o = obs.get_observation(obs_id)
    return o.to_dict() if o else None


def transition_observation(obs_id: str, to_status: str, *, user: str = "", note: str = "") -> dict[str, Any]:
    return obs.transition(obs_id, to_status, user=user, note=note).to_dict()


def observation_summary() -> dict[str, Any]:
    return obs.summary()


# --------------------------------------------------------------------------- #
# Evidence repository
# --------------------------------------------------------------------------- #
def repository_search(**filters) -> list[dict[str, Any]]:
    """Search Evidence Repository using the Phase-1 authoritative read facade.

    Merges in-process uploads with audit/canonical artifacts so a just-returned
    Evidence ID is immediately resolvable (same ID, no alternate namespace).
    """
    try:
        from modules.shared.services.evidence_authoritative_reader import (
            collect_authoritative_evidence_rows,
        )

        rows = collect_authoritative_evidence_rows(
            latest_only=bool(filters.get("latest_only", True)),
        )
    except Exception:  # noqa: BLE001 - fall back to engine search
        return [a.to_dict() for a in repo.search(**filters)]

    technology = str(filters.get("technology") or "").strip()
    framework = str(filters.get("framework") or "").strip()
    query = str(filters.get("query") or "").strip().lower()
    if technology:
        rows = [r for r in rows if str(r.get("technology") or "") == technology]
    if framework:
        rows = [
            r for r in rows
            if framework in (r.get("frameworks") or [])
            or framework == str(r.get("framework") or "")
        ]
    if query:
        rows = [
            r for r in rows
            if query in " ".join(
                str(r.get(k) or "")
                for k in (
                    "evidence_id",
                    "display_evidence_id",
                    "evidence_key",
                    "filename",
                    "control",
                    "control_id",
                    "application",
                    "framework",
                    "source_connector",
                    "sha256",
                )
            ).lower()
        ]
    return rows


def evidence_versions(evidence_key: str) -> list[dict[str, Any]]:
    """Return version history for an evidence_key (or evidence_id fallback).

    Reuses the existing audit store query. Triggers the same hydration path as
    ``repository_search`` so newly mirrored versions are visible, then falls
    back to the authoritative row when the key is ops-only.
    """
    key = str(evidence_key or "").strip()
    if not key:
        return []

    # Reuse search() hydration (SQL + canonical) — same queries as list path.
    try:
        repo.search(latest_only=True)
    except Exception:  # noqa: BLE001
        pass

    versions = [a.to_dict() for a in repo.get_versions(key)]
    if versions:
        return versions

    # Resolve when callers pass evidence_id / display id instead of evidence_key.
    try:
        from modules.shared.services.evidence_authoritative_reader import (
            collect_authoritative_evidence_rows,
            get_authoritative_evidence,
        )

        auth = get_authoritative_evidence(key)
        if auth and auth.get("evidence_key"):
            versions = [a.to_dict() for a in repo.get_versions(str(auth["evidence_key"]))]
            if versions:
                return versions
            return [_authoritative_row_as_version(auth)]

        matches = [
            r for r in collect_authoritative_evidence_rows(latest_only=False)
            if str(r.get("evidence_key") or "") == key
        ]
        if matches:
            # Prefer rows that already carry version metadata; keep order by version.
            matches.sort(key=lambda r: int(r.get("version") or 1))
            # If AI store empty for this key, surface authoritative metadata as vN.
            store_versions = [a.to_dict() for a in repo.get_versions(key)]
            if store_versions:
                return store_versions
            return [_authoritative_row_as_version(r) for r in matches]
    except Exception:  # noqa: BLE001
        pass
    return []


def _authoritative_row_as_version(row: dict[str, Any]) -> dict[str, Any]:
    """Map an authoritative list row into the versions-API shape (no new store)."""
    meta = dict(row.get("metadata") or {}) if isinstance(row.get("metadata"), dict) else {}
    return {
        "evidence_key": row.get("evidence_key") or "",
        "evidence_id": row.get("evidence_id") or "",
        "display_evidence_id": row.get("display_evidence_id") or meta.get("display_evidence_id") or "",
        "version": int(row.get("version") or 1),
        "filename": row.get("filename") or "",
        "original_filename": row.get("original_filename") or meta.get("original_filename") or "",
        "application": row.get("application") or "",
        "asset_id": row.get("application") or "",
        "framework": row.get("framework") or "",
        "frameworks": row.get("framework_tags") or ([row.get("framework")] if row.get("framework") else []),
        "control": row.get("control") or row.get("control_id") or "",
        "control_id": row.get("control_id") or row.get("control") or "",
        "technology": row.get("technology") or "",
        "verdict": row.get("verdict") or "",
        "checksum": row.get("checksum") or "",
        "sha256": row.get("sha256") or "",
        "content_hash": row.get("sha256") or "",
        "custody_mode": row.get("custody_mode") or "",
        "object_uri": row.get("object_uri") or "",
        "source_url": row.get("source_url") or "",
        "source_connector": row.get("source_connector") or "",
        "collected_at": row.get("collected_at") or row.get("uploaded_at") or "",
        "tags": row.get("tags") or [],
        "metadata": meta,
    }


def evidence_timeline(evidence_key: str = "") -> list[dict[str, Any]]:
    return repo.timeline(evidence_key)


def repository_stats() -> dict[str, Any]:
    """KPI stats aligned with the authoritative repository list (same rows)."""
    try:
        from modules.shared.services.evidence_authoritative_reader import (
            collect_authoritative_evidence_rows,
        )

        rows = collect_authoritative_evidence_rows(latest_only=True)
        technologies = {
            str(r.get("technology") or "").strip()
            for r in rows
            if str(r.get("technology") or "").strip()
        }
        engine = repo.stats()
        return {
            "evidence_keys": len(rows),
            "total_versions": max(int(engine.get("total_versions", 0) or 0), len(rows)),
            "latest_count": len(rows),
            "technologies": len(technologies),
            "by_technology": engine.get("by_technology") or {},
            "by_verdict": engine.get("by_verdict") or {},
            "timeline_events": int(engine.get("timeline_events", 0) or 0),
        }
    except Exception:  # noqa: BLE001 - fall back to engine stats
        return repo.stats()


# --------------------------------------------------------------------------- #
# Packs
# --------------------------------------------------------------------------- #
def build_pack(pack_type: str, scope: str, *, asset_ids: list[str] | None = None) -> dict[str, Any] | None:
    """Build a pack by type: evidence|framework|asset|application|technology."""
    kind = (pack_type or "").strip().lower()
    if kind == "framework":
        return packs.framework_pack(scope)
    if kind == "asset":
        return packs.asset_pack(scope)
    if kind == "technology":
        return packs.technology_pack(scope)
    if kind == "application":
        return packs.application_pack(scope, asset_ids or [])
    if kind == "evidence":
        keys = [k for k in (scope or "").split(",") if k]
        return packs.evidence_pack(keys)
    return None


def verify_pack(manifest: dict[str, Any]) -> bool:
    return packs.verify_manifest(manifest)
