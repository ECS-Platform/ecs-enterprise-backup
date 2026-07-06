"""Tests for scripts/run_ecs_demo_smoke.py — the demo smoke runner (offline)."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

demo = importlib.import_module("scripts.run_ecs_demo_smoke")


def test_run_smoke_all_pass():
    report = demo.run_smoke()
    assert report["ok"] is True, [c for c in report["checks"] if not c["ok"]]
    assert report["passed"] == report["total"]
    names = {c["check"] for c in report["checks"]}
    for expected in (
        "predefined_query_catalog", "audit_intelligence_services_import",
        "mocked_asset_discovery", "technology_control_mapping",
        "evidence_orchestration", "evidence_validation", "observation_generation",
        "evidence_pack_manifest", "dashboard_aggregation", "integration_adapters",
    ):
        assert expected in names


def test_render_contains_result_line():
    report = demo.run_smoke()
    text = demo.render(report)
    assert "ECS Demo Smoke Check" in text
    assert "Result:" in text


def test_main_returns_zero_and_valid_json(capsys):
    rc = demo.main(["--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["ok"] is True
    assert data["total"] == 10
