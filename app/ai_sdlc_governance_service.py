"""AI & SDLC Governance — presentation service (mock data only)."""

from __future__ import annotations

from app.ai_sdlc_governance_mock import (
    build_ai_posture,
    build_ai_registry,
    build_sdlc_gates,
    build_sdlc_stage_detail,
    drill_posture,
    drill_registry,
    drill_sdlc,
)


def posture_view() -> dict:
    return build_ai_posture()


def sdlc_gates_view(release_id: str = "") -> dict:
    return build_sdlc_gates(release_id)


def sdlc_stage_view(stage_key: str, release_id: str = "") -> dict:
    return build_sdlc_stage_detail(stage_key, release_id)


def registry_view() -> dict:
    return build_ai_registry()


def posture_drill(metric: str, item_id: str = "") -> dict:
    return drill_posture(metric, item_id)


def registry_drill(section: str, item_id: str = "") -> dict:
    return drill_registry(section, item_id)


def sdlc_drill(metric: str, release_id: str = "", stage_key: str = "", item_id: str = "") -> dict:
    return drill_sdlc(metric, release_id, stage_key, item_id)
