"""Tests for the Cross-Application Comparison gap export (Phase 3 UC: comparison)."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")

import pytest

from modules.governance.engines.comparison_engine import ALL_FRAMEWORKS
from modules.governance.engines.gap_export_engine import (
    build_gap_export_payload,
    generate_gap_export_file,
)


@pytest.mark.parametrize("framework", ["All Frameworks", *ALL_FRAMEWORKS])
@pytest.mark.parametrize("fmt", ["excel", "csv", "pdf"])
def test_gap_export_does_not_raise_for_every_framework(framework, fmt):
    """Regression: frameworks with < 3 entries in CONTROL_IDS (or none at all)
    used to raise IndexError in _gap_detail_rows via `ids[i % 3]`."""
    payload = build_gap_export_payload(
        framework=framework,
        scope="All Applications",
        time_range="Current Month",
        application="All Applications",
        role="cio",
        include_executive=True,
        include_observations=True,
        include_failed=True,
        include_missing=True,
        include_audit_impact=True,
    )
    content, media_type, filename = generate_gap_export_file(payload, fmt)
    assert content
    assert filename
