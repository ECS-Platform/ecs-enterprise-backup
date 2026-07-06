"""Tests for the Technology -> Control -> Framework mapping engine (M1, Module 1).

Deterministic and offline: derives everything from the existing predefined-query
catalog (167 controls). No live Docker / DB required.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import technology_control_mapping as mapping
from modules.audit_intelligence.services import mapping_service as svc
from modules.audit_intelligence.models import ControlRef, FrameworkRef, TechnologyRef


@pytest.fixture(autouse=True)
def _fresh_cache():
    mapping.reset_cache()
    yield
    mapping.reset_cache()


# --------------------------------------------------------------------------- #
# Catalog projection
# --------------------------------------------------------------------------- #
def test_all_controls_nonempty_and_typed():
    controls = mapping.all_controls()
    assert len(controls) >= 100  # 167 today; guard against accidental emptiness
    assert all(isinstance(c, ControlRef) for c in controls)
    assert all(c.control_id for c in controls)


def test_stats_shape_and_consistency():
    stats = mapping.mapping_stats()
    assert stats["controls"] == len(mapping.all_controls())
    assert stats["technologies"] == len(mapping.list_technologies())
    assert stats["frameworks"] == len(mapping.list_frameworks())
    assert stats["executable_controls"] <= stats["controls"]


def test_control_ids_are_unique():
    ids = [c.control_id for c in mapping.all_controls()]
    assert len(ids) == len(set(ids)), "duplicate control_ids in mapping projection"


# --------------------------------------------------------------------------- #
# Technologies
# --------------------------------------------------------------------------- #
def test_list_technologies_have_counts():
    techs = mapping.list_technologies()
    assert techs and all(isinstance(t, TechnologyRef) for t in techs)
    for t in techs:
        assert t.control_count == len(t.control_ids)
        assert t.control_count > 0


def test_expected_technologies_present():
    names = set(mapping.technology_names())
    for expected in ("NGINX", "PostgreSQL", "Oracle", "Redis", "MongoDB", "Kubernetes"):
        assert expected in names


def test_nginx_maps_to_expected_controls_and_frameworks():
    """The canonical example chain: NGINX -> NGX-* -> TLS -> RBI/PCI/... ."""
    controls = mapping.controls_for_technology("NGINX")
    ids = {c.control_id for c in controls}
    # NGX-001..008 are the NGINX supplementary controls.
    assert {"NGX-001", "NGX-002"}.issubset(ids)

    frameworks = mapping.frameworks_for_technology("NGINX")
    assert "RBI Cyber Security" in frameworks
    assert "PCI DSS" in frameworks


def test_technology_lookup_is_case_insensitive():
    assert mapping.get_technology("nginx") is not None
    assert mapping.get_technology("NGINX") is not None
    assert mapping.get_technology("does-not-exist") is None


# --------------------------------------------------------------------------- #
# Frameworks
# --------------------------------------------------------------------------- #
def test_list_frameworks_have_counts():
    fws = mapping.list_frameworks()
    assert fws and all(isinstance(f, FrameworkRef) for f in fws)
    for f in fws:
        assert f.control_count == len(f.control_ids)
        assert f.technology_count == len(f.technologies)


def test_framework_to_technologies_roundtrip():
    # Pick a framework that NGINX participates in and assert NGINX is listed.
    fw = "PCI DSS"
    techs = mapping.technologies_for_framework(fw)
    assert "NGINX" in techs
    # And every control for that framework indeed references it.
    for c in mapping.controls_for_framework(fw):
        assert fw in c.frameworks


def test_frameworks_for_control_and_technology_for_control():
    control = mapping.controls_for_technology("NGINX")[0]
    fws = mapping.frameworks_for_control(control.control_id)
    assert set(fws) == set(control.frameworks)
    assert mapping.technology_for_control(control.control_id) == "NGINX"
    assert mapping.technology_for_control("NOPE-999") is None


# --------------------------------------------------------------------------- #
# Graph + search
# --------------------------------------------------------------------------- #
def test_build_mapping_graph_structure():
    graph = mapping.build_mapping_graph()
    assert "technologies" in graph and "stats" in graph
    nginx = next(t for t in graph["technologies"] if t["technology"] == "NGINX")
    assert nginx["control_count"] == len(nginx["controls"])
    assert all("frameworks" in c for c in nginx["controls"])


def test_mapping_rows_one_per_control():
    rows = mapping.mapping_rows()
    assert len(rows) == len(mapping.all_controls())


def test_search_by_technology_filter():
    rows = mapping.search_mappings(technology="NGINX")
    assert rows and all(r.technology == "NGINX" for r in rows)


def test_search_by_framework_filter():
    rows = mapping.search_mappings(framework="PCI DSS")
    assert rows and all("PCI DSS" in r.frameworks for r in rows)


def test_search_by_free_text():
    rows = mapping.search_mappings(query="ngx-001")
    assert any(r.control_id == "NGX-001" for r in rows)


def test_search_combined_filters_narrow():
    broad = mapping.search_mappings(technology="NGINX")
    narrow = mapping.search_mappings(technology="NGINX", framework="PCI DSS")
    assert len(narrow) <= len(broad)


# --------------------------------------------------------------------------- #
# Service facade (serialization)
# --------------------------------------------------------------------------- #
def test_service_returns_serializable_dicts():
    techs = svc.technologies()
    assert techs and isinstance(techs[0], dict)
    assert isinstance(techs[0]["control_ids"], list)

    graph = svc.graph()
    assert isinstance(graph, dict) and "technologies" in graph

    detail = svc.technology_detail("NGINX")
    assert detail and isinstance(detail["controls"], list)
    assert svc.technology_detail("nope") is None


def test_service_filter_options():
    opts = svc.filter_options()
    assert opts["technologies"][0] == "All Technologies"
    assert opts["frameworks"][0] == "All Frameworks"
    assert "NGINX" in opts["technologies"]
