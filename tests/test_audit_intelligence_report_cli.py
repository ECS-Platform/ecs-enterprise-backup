"""Tests for scripts/audit_intelligence_report.py (M1 CLI harness).

Read-only, offline. Exercises the mapping and asset sections and JSON/text output
without any live Docker / network. The asset section uses the offline
docker-compose parse (real repo file) and the enterprise-GRC CMDB.
"""

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

cli = importlib.import_module("scripts.audit_intelligence_report")


def _args(**over):
    base = dict(
        section="all", technology="", framework="",
        docker_compose=False, enterprise_grc=False, json=False,
    )
    base.update(over)
    import argparse

    return argparse.Namespace(**base)


# --------------------------------------------------------------------------- #
# Report building
# --------------------------------------------------------------------------- #
def test_mapping_overview_report():
    report = cli.build_report(_args(section="mapping"))
    assert "mapping" in report
    stats = report["mapping"]["stats"]
    assert stats["controls"] >= 100
    assert stats["technologies"] >= 1
    assert any(t["name"] == "NGINX" for t in report["mapping"]["technologies"])


def test_mapping_technology_detail():
    report = cli.build_report(_args(section="mapping", technology="NGINX"))
    m = report["mapping"]
    assert m["kind"] == "technology_detail"
    assert m["detail"]["name"] == "NGINX"
    assert m["detail"]["controls"]


def test_mapping_framework_detail():
    report = cli.build_report(_args(section="mapping", framework="PCI DSS"))
    m = report["mapping"]
    assert m["kind"] == "framework_detail"
    assert m["detail"]["name"] == "PCI DSS"


def test_mapping_unknown_technology_detail_is_none():
    report = cli.build_report(_args(section="mapping", technology="does-not-exist"))
    assert report["mapping"]["detail"] is None


def test_assets_section_docker_compose_offline():
    report = cli.build_report(_args(section="assets", docker_compose=True))
    a = report["assets"]
    assert a["coverage"]["total_assets"] > 0
    assert a["sources"]["docker_compose"] is True
    assert isinstance(a["technology_inventory"], list)


def test_assets_section_defaults_to_compose_when_none_selected():
    # `--section assets` with no source flags should still populate (compose default).
    report = cli.build_report(_args(section="assets"))
    assert report["assets"]["sources"]["docker_compose"] is True


def test_assets_section_enterprise_grc():
    report = cli.build_report(_args(section="assets", enterprise_grc=True))
    assert report["assets"]["coverage"]["total_assets"] > 0


# --------------------------------------------------------------------------- #
# Rendering / output modes
# --------------------------------------------------------------------------- #
def test_render_text_contains_headers():
    report = cli.build_report(_args(section="all", docker_compose=True))
    text = cli.render_text(report)
    assert "Audit Intelligence Report" in text
    assert "Technology -> Control -> Framework mapping" in text
    assert "Asset inventory & fingerprints" in text


def test_main_json_mode_is_valid(capsys):
    rc = cli.main(["--section", "mapping", "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)  # must be valid JSON
    assert data["section"] == "mapping"
    assert "mapping" in data


def test_main_text_mode_runs(capsys):
    rc = cli.main(["--section", "mapping"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Technologies:" in out


def test_main_all_sections_runs(capsys):
    rc = cli.main(["--section", "all", "--docker-compose"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "mapping" not in out.lower() or "Asset inventory" in out
