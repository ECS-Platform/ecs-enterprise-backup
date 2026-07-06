"""Catalog tests for the extended technology expansion.

Covers Redis, Apache HTTPD, Tomcat, SQL Server, MongoDB, Kubernetes, OpenShift:
presence, counts, exact technology labels, uniqueness, the 167 total, and that
the earlier controls remain intact. No live targets required.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.operations.engines import predefined_queries_engine as engine
from modules.operations.engines import supplementary_query_catalog as catalog

RDX = [f"RDX-00{i}" for i in range(1, 9)]
APX = [f"APX-00{i}" for i in range(1, 9)]
TCX = [f"TCX-00{i}" for i in range(1, 9)]
MSX = [f"MSX-0{i:02d}" for i in range(1, 11)]
MGX = [f"MGX-00{i}" for i in range(1, 9)]
K8X = [f"K8X-0{i:02d}" for i in range(1, 11)]
OCX = [f"OCX-0{i:02d}" for i in range(1, 11)]

EXPECTED = {
    "Redis": (RDX, 8),
    "Apache HTTPD": (APX, 8),
    "Tomcat": (TCX, 8),
    "SQL Server": (MSX, 10),
    "MongoDB": (MGX, 8),
    "Kubernetes": (K8X, 10),
    "OpenShift": (OCX, 10),
}

# Earlier expansion (must remain intact)
PRIOR_IDS = (
    [f"PGX-00{i}" for i in range(1, 9)]
    + [f"YBX-00{i}" for i in range(1, 9)]
    + [f"MYX-0{i:02d}" for i in range(1, 11)]
    + [f"ORX-0{i:02d}" for i in range(1, 11)]
    + [f"NGX-00{i}" for i in range(1, 9)]
    + [f"LNX-00{i}" for i in range(1, 9)]
    + [f"RH8-00{i}" for i in range(1, 9)]
    + [f"RH9-00{i}" for i in range(1, 9)]
)


def test_new_catalog_counts():
    sup = catalog.supplementary_controls()
    by_tech: dict[str, list[str]] = {}
    for c in sup:
        by_tech.setdefault(c["technology"], []).append(c["control_id"])
    total_new = 0
    for tech, (_ids, count) in EXPECTED.items():
        assert len(by_tech.get(tech, [])) == count, f"{tech} count wrong"
        total_new += count
    assert total_new == 62


@pytest.mark.parametrize("tech", list(EXPECTED.keys()))
def test_new_ids_present(tech):
    engine.load_predefined_queries(force=True)
    ids, _ = EXPECTED[tech]
    for cid in ids:
        ctrl = engine.get_control_by_id(cid)
        assert ctrl is not None, f"{cid} missing"
        assert ctrl["technology"] == tech
        assert ctrl["query"], f"{cid} has no command/query"
        assert ctrl.get("category"), f"{cid} missing category"
        assert ctrl.get("evidence_type"), f"{cid} missing expected evidence"


def test_exact_technology_labels():
    engine.load_predefined_queries(force=True)
    assert engine.get_control_by_id("RDX-001")["technology"] == "Redis"
    assert engine.get_control_by_id("APX-001")["technology"] == "Apache HTTPD"
    assert engine.get_control_by_id("TCX-001")["technology"] == "Tomcat"
    assert engine.get_control_by_id("MSX-001")["technology"] == "SQL Server"
    assert engine.get_control_by_id("MGX-001")["technology"] == "MongoDB"
    assert engine.get_control_by_id("K8X-001")["technology"] == "Kubernetes"
    assert engine.get_control_by_id("OCX-001")["technology"] == "OpenShift"


def test_no_duplicate_ids():
    ids = [c["control_id"] for c in catalog.supplementary_controls()]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, f"duplicate ids: {dupes}"


def test_total_is_167():
    rep = engine.load_predefined_queries(force=True)
    # 37 Excel + 130 supplementary (68 prior + 62 new)
    assert rep["controls_loaded"] == 167


def test_prior_controls_intact():
    engine.load_predefined_queries(force=True)
    for cid in PRIOR_IDS:
        assert engine.get_control_by_id(cid) is not None, f"prior control {cid} lost"


def test_technology_filter_includes_all_new():
    dash = engine.get_predefined_queries_dashboard(per_page=1)
    opts = dash["technology_options"]
    for tech in EXPECTED:
        assert tech in opts


@pytest.mark.parametrize("term,count", [("RDX", 8), ("APX", 8), ("TCX", 8),
                                        ("MSX", 10), ("MGX", 8), ("K8X", 10), ("OCX", 10)])
def test_search_counts(term, count):
    dash = engine.get_predefined_queries_dashboard(search=term, per_page=50)
    found = [r for r in dash["rows"] if r["control_id"].startswith(term)]
    assert len(found) == count


@pytest.mark.parametrize("tech,prefix,count", [
    ("Redis", "RDX", 8), ("Apache HTTPD", "APX", 8), ("Tomcat", "TCX", 8),
    ("SQL Server", "MSX", 10), ("MongoDB", "MGX", 8),
    ("Kubernetes", "K8X", 10), ("OpenShift", "OCX", 10),
])
def test_technology_filter_narrows(tech, prefix, count):
    dash = engine.get_predefined_queries_dashboard(technology=tech, per_page=50)
    assert all((r.get("technology") or "") == tech for r in dash["rows"])
    ids = {r["control_id"] for r in dash["rows"]}
    assert len([i for i in ids if i.startswith(prefix)]) == count
