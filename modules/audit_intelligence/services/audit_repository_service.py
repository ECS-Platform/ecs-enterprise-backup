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
    return [a.to_dict() for a in repo.search(**filters)]


def evidence_versions(evidence_key: str) -> list[dict[str, Any]]:
    return [a.to_dict() for a in repo.get_versions(evidence_key)]


def evidence_timeline(evidence_key: str = "") -> list[dict[str, Any]]:
    return repo.timeline(evidence_key)


def repository_stats() -> dict[str, Any]:
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
