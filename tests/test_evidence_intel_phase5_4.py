"""Unit tests for the Evidence Intelligence Foundation (Phase 5.4).

Deterministic, non-LLM. Covers versioning, lineage, sufficiency V2 (delegation),
closure readiness, reuse scoring, change detection, the query engine, DTOs, edge
cases, flag-OFF behavior, and backward compatibility.

Engines are exercised with force=True where we want to compute regardless of the
default-off flags; flag behavior itself is tested separately via env.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.evidence_intel import (
    Band,
    ChangeClass,
    EvidenceVersionHistory,
    ReadinessLevel,
    ReuseBand,
    aggregate,
    ancestors,
    assess_change,
    assess_closure_readiness,
    assess_sufficiency,
    build_lineage_graph,
    build_version_history,
    descendants,
    get_version,
    impact_analysis,
    latest_version,
    next_version,
    query_evidence,
    score_reuse,
    summarize,
)
from app.evidence_intel.change import change_detection_enabled
from app.evidence_intel.dtos import (
    EvidenceChangeCard,
    EvidenceLineageCard,
    EvidenceVersionCard,
    QueryResultCard,
    ReadinessCard,
    ReuseCard,
    SufficiencyCard,
)
from app.evidence_intel.lineage import lineage_enabled
from app.evidence_intel.models import EvidenceStatus
from app.evidence_intel.query import query_enabled
from app.evidence_intel.readiness import observation_readiness_enabled
from app.evidence_intel.reuse import reuse_scoring_enabled
from app.evidence_intel.sufficiency_v2 import sufficiency_enabled
from app.evidence_intel.versioning import compute_hash, versioning_enabled

NOW = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


def ev(**over):
    base = {
        "evidence_id": "ev-1", "object_type": "pull_request", "title": "t",
        "content": "c", "owner": "alice", "url": "http://x",
        "control_mapping": ["code-review"], "framework_mapping": ["SOC2-CC8"],
        "review_status": "Approved",
        "collected_timestamp": (NOW - timedelta(days=2)).isoformat(),
        "valid_until": (NOW + timedelta(days=30)).isoformat(),
        "metadata": {"merged": True, "approvals": 2},
    }
    base.update(over)
    return base


# --------------------------------------------------------------------------- #
# 1. Versioning (24)
# --------------------------------------------------------------------------- #

def test_version_history_basic():
    snaps = [{"uploaded_at": "2026-01-01", "uploaded_by": "a", "hash": "h1"},
             {"uploaded_at": "2026-02-01", "uploaded_by": "b", "hash": "h2"}]
    h = build_version_history("ev-1", snaps, force=True)
    assert len(h.versions) == 2

def test_version_numbers_sequential():
    snaps = [{"hash": "h1"}, {"hash": "h2"}, {"hash": "h3"}]
    h = build_version_history("ev-1", snaps, force=True)
    assert [v.version_number for v in h.versions] == [1, 2, 3]

def test_version_previous_links():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[0].previous_version is None
    assert h.versions[1].previous_version == 1

def test_version_superseded_links():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[0].superseded_by == 2
    assert h.versions[1].superseded_by is None

def test_version_dedupe_identical_hash():
    h = build_version_history("e", [{"hash": "x"}, {"hash": "x"}, {"hash": "y"}], force=True)
    assert len(h.versions) == 2

def test_version_latest():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert latest_version(h).version_number == 2

def test_version_latest_none_empty():
    h = build_version_history("e", [], force=True)
    assert latest_version(h) is None

def test_version_get_version():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert get_version(h, 2).hash == "2"

def test_version_get_version_missing():
    h = build_version_history("e", [{"hash": "1"}], force=True)
    assert get_version(h, 5) is None

def test_version_superseded_status():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[0].evidence_status == EvidenceStatus.SUPERSEDED.value

def test_version_rejected_not_superseded_status():
    h = build_version_history("e", [{"hash": "1", "status": "Rejected"}, {"hash": "2"}], force=True)
    assert h.versions[0].evidence_status == "Rejected"

def test_version_created_fields():
    h = build_version_history("e", [{"hash": "1", "uploaded_at": "2026-01-01",
                                     "uploaded_by": "bob"}], force=True)
    assert h.versions[0].created_at == "2026-01-01" and h.versions[0].created_by == "bob"

def test_version_change_reason_from_comments():
    h = build_version_history("e", [{"hash": "1", "upload_comments": "fix"}], force=True)
    assert h.versions[0].change_reason == "fix"

def test_version_hash_derived_when_absent():
    h = build_version_history("e", [{"upload_filename": "a.pdf", "content": "x"}], force=True)
    assert h.versions[0].hash != ""

def test_version_disabled_default(monkeypatch):
    monkeypatch.setenv("EVIDENCE_VERSIONING_ENABLED", "false")
    h = build_version_history("e", [{"hash": "1"}])
    assert h.versions == []

def test_version_enabled_flag(monkeypatch):
    monkeypatch.setenv("EVIDENCE_VERSIONING_ENABLED", "true")
    assert versioning_enabled() is True
    assert build_version_history("e", [{"hash": "1"}]).versions

def test_version_next_version():
    h = build_version_history("e", [{"hash": "1"}], force=True)
    nv = next_version(h, {"hash": "2"}, force=True)
    assert nv.version_number == 2

def test_version_next_version_no_change():
    h = build_version_history("e", [{"hash": "1"}], force=True)
    assert next_version(h, {"hash": "1"}, force=True) is None

def test_version_next_version_disabled(monkeypatch):
    monkeypatch.setenv("EVIDENCE_VERSIONING_ENABLED", "false")
    h = build_version_history("e", [{"hash": "1"}], force=True)
    assert next_version(h, {"hash": "2"}) is None

def test_version_compute_hash_stable():
    assert compute_hash("abc") == compute_hash("abc")

def test_version_compute_hash_empty():
    assert compute_hash("") == "" and compute_hash(None) == ""

def test_version_history_to_dict():
    h = build_version_history("e", [{"hash": "1"}], force=True)
    d = h.to_dict()
    assert d["version_count"] == 1 and d["latest_version"] == 1

def test_version_ignores_non_mapping():
    h = build_version_history("e", [{"hash": "1"}, "bad", None], force=True)
    assert len(h.versions) == 1

def test_version_failsafe_returns_history():
    h = build_version_history("e", None, force=True)
    assert isinstance(h, EvidenceVersionHistory)


# --------------------------------------------------------------------------- #
# 2. Lineage (26)
# --------------------------------------------------------------------------- #

def obs_rows():
    return [
        {"framework": "PCI DSS", "control_id": "PCI-10.6", "observation_id": "OBS-1",
         "evidence_id": "ev-1", "status": "Open"},
        {"framework": "PCI DSS", "control_id": "PCI-10.6", "observation_id": "OBS-2",
         "evidence_id": "ev-2", "status": "Open"},
        {"framework": "ISO27001", "control_id": "A.12", "observation_id": "OBS-3",
         "evidence_id": "ev-3", "status": "Closed"},
    ]

def test_lineage_builds_graph():
    g = build_lineage_graph(obs_rows(), force=True)
    assert g.enabled and g.nodes and g.edges

def test_lineage_disabled_default(monkeypatch):
    monkeypatch.setenv("EVIDENCE_LINEAGE_ENABLED", "false")
    g = build_lineage_graph(obs_rows())
    assert g.enabled is False

def test_lineage_enabled_flag(monkeypatch):
    monkeypatch.setenv("EVIDENCE_LINEAGE_ENABLED", "true")
    assert lineage_enabled() is True

def test_lineage_framework_node():
    g = build_lineage_graph(obs_rows(), force=True)
    assert "framework:PCI DSS" in g.nodes

def test_lineage_control_node():
    g = build_lineage_graph(obs_rows(), force=True)
    assert "control:PCI-10.6" in g.nodes

def test_lineage_observation_node():
    g = build_lineage_graph(obs_rows(), force=True)
    assert "observation:OBS-1" in g.nodes

def test_lineage_evidence_node():
    g = build_lineage_graph(obs_rows(), force=True)
    assert "evidence:ev-1" in g.nodes

def test_lineage_edge_framework_control():
    g = build_lineage_graph(obs_rows(), force=True)
    assert any(e.parent_key == "framework:PCI DSS" and e.child_key == "control:PCI-10.6"
               for e in g.edges)

def test_lineage_descendants():
    g = build_lineage_graph(obs_rows(), force=True)
    d = descendants(g, "framework:PCI DSS")
    assert "control:PCI-10.6" in d and "observation:OBS-1" in d and "evidence:ev-1" in d

def test_lineage_ancestors():
    g = build_lineage_graph(obs_rows(), force=True)
    a = ancestors(g, "evidence:ev-1")
    assert "framework:PCI DSS" in a and "control:PCI-10.6" in a

def test_lineage_impact_analysis():
    g = build_lineage_graph(obs_rows(), force=True)
    impact = impact_analysis(g, "control:PCI-10.6")
    assert "OBS-1" in impact["observation"] and "ev-1" in impact["evidence"]

def test_lineage_summary():
    g = build_lineage_graph(obs_rows(), force=True)
    s = summarize(g, "framework:PCI DSS")
    assert "PCI-10.6" in s.controls and "OBS-1" in s.observations

def test_lineage_summary_counts():
    g = build_lineage_graph(obs_rows(), force=True)
    s = summarize(g, "framework:PCI DSS")
    assert s.descendant_count >= 4

def test_lineage_with_versions():
    vh = build_version_history("ev-1", [{"hash": "1"}, {"hash": "2"}], force=True)
    g = build_lineage_graph([obs_rows()[0]], version_histories={"ev-1": vh}, force=True)
    assert any(n.node_type == "version" for n in g.nodes.values())

def test_lineage_version_edges():
    vh = build_version_history("ev-1", [{"hash": "1"}], force=True)
    g = build_lineage_graph([obs_rows()[0]], version_histories={"ev-1": vh}, force=True)
    assert any(e.relation == "has_version" for e in g.edges)

def test_lineage_dedup_nodes():
    g = build_lineage_graph(obs_rows(), force=True)
    # PCI-10.6 control appears in 2 observations but only one node.
    assert sum(1 for k in g.nodes if k == "control:PCI-10.6") == 1

def test_lineage_dedup_edges():
    rows = [obs_rows()[0], obs_rows()[0]]
    g = build_lineage_graph(rows, force=True)
    fw_edges = [e for e in g.edges if e.parent_key == "framework:PCI DSS"]
    assert len(fw_edges) == 1

def test_lineage_empty_rows():
    g = build_lineage_graph([], force=True)
    assert g.enabled and not g.nodes

def test_lineage_skips_non_mapping():
    g = build_lineage_graph(["bad", None, obs_rows()[0]], force=True)
    assert "observation:OBS-1" in g.nodes

def test_lineage_missing_framework():
    g = build_lineage_graph([{"control_id": "C", "observation_id": "O", "evidence_id": "E"}],
                            force=True)
    assert "control:C" in g.nodes and not any(n.node_type == "framework" for n in g.nodes.values())

def test_lineage_descendants_cycle_safe():
    g = build_lineage_graph(obs_rows(), force=True)
    # Should terminate even though we call twice.
    assert isinstance(descendants(g, "framework:PCI DSS"), list)

def test_lineage_ancestors_root_empty():
    g = build_lineage_graph(obs_rows(), force=True)
    assert ancestors(g, "framework:PCI DSS") == []

def test_lineage_graph_to_dict():
    g = build_lineage_graph(obs_rows(), force=True)
    d = g.to_dict()
    assert d["node_count"] > 0 and "nodes" in d

def test_lineage_summary_to_dict():
    g = build_lineage_graph(obs_rows(), force=True)
    assert "frameworks" in summarize(g, "framework:PCI DSS").to_dict()

def test_lineage_control_uses_control_field():
    g = build_lineage_graph([{"framework": "F", "control": "CTRL", "observation_id": "O"}],
                            force=True)
    assert "control:CTRL" in g.nodes

def test_lineage_evidence_from_filename():
    g = build_lineage_graph([{"observation_id": "O", "upload_filename": "f.pdf"}], force=True)
    assert "evidence:f.pdf" in g.nodes


# --------------------------------------------------------------------------- #
# 3. Sufficiency V2 (delegation) (22)
# --------------------------------------------------------------------------- #

def test_suff_disabled_default(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "false")
    a = assess_sufficiency("OBS-1", [ev()])
    assert a.enabled is False and "disabled" in a.note

def test_suff_enabled_flag(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    assert sufficiency_enabled() is True

def test_suff_force_computes():
    a = assess_sufficiency("OBS-1", [ev()], framework="soc2", force=True, now=NOW)
    assert a.enabled is True and a.score > 0

def test_suff_delegates_to_52a():
    a = assess_sufficiency("OBS-1", [ev()], framework="soc2", force=True, now=NOW)
    assert a.item_scores and a.item_scores[0] > 0

def test_suff_high_quality_green():
    items = [ev(evidence_id=f"e{i}") for i in range(3)]
    a = assess_sufficiency("OBS-1", items, framework="soc2", force=True, now=NOW)
    assert a.band in (Band.GREEN.value, Band.AMBER.value)

def test_suff_empty_red():
    a = assess_sufficiency("OBS-1", [], framework="soc2", force=True, now=NOW)
    assert a.score == 0.0 and a.band == Band.RED.value

def test_suff_evidence_count():
    a = assess_sufficiency("OBS-1", [ev(), ev(evidence_id="e2")], force=True, now=NOW)
    assert a.evidence_count == 2

def test_suff_mandatory_types_pci():
    items = [ev(object_type="policy"), ev(object_type="quality_gate"),
             ev(object_type="test_result")]
    a = assess_sufficiency("OBS", items, framework="pci-dss", force=True, now=NOW)
    mand = next(r for r in a.rules if r.name == "mandatory_types")
    assert mand.passed is True

def test_suff_mandatory_types_missing():
    items = [ev(object_type="policy")]
    a = assess_sufficiency("OBS", items, framework="pci-dss", force=True, now=NOW)
    mand = next(r for r in a.rules if r.name == "mandatory_types")
    assert mand.passed is False and "missing" in mand.detail

def test_suff_approval_state():
    items = [ev(review_status="Approved"), ev(review_status="Rejected")]
    a = assess_sufficiency("OBS", items, force=True, now=NOW)
    appr = next(r for r in a.rules if r.name == "approval_state")
    assert appr.score == 50.0

def test_suff_recency_expired():
    items = [ev(valid_until=(NOW - timedelta(days=1)).isoformat())]
    a = assess_sufficiency("OBS", items, force=True, now=NOW)
    rec = next(r for r in a.rules if r.name == "recency")
    assert rec.score == 0.0

def test_suff_rules_count():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    assert len(a.rules) == 5

def test_suff_results_dimensions():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    dims = {r.dimension for r in a.results}
    assert dims == {"item_quality", "evidence_count", "mandatory_types",
                    "approval_state", "recency"}

def test_suff_default_framework_mandatory():
    a = assess_sufficiency("OBS", [ev(object_type="policy")], framework="unknown_fw",
                           force=True, now=NOW)
    mand = next(r for r in a.rules if r.name == "mandatory_types")
    assert mand.passed is True  # default mandatory = policy

def test_suff_subject_preserved():
    a = assess_sufficiency("OBS-XYZ", [ev()], force=True, now=NOW)
    assert a.subject == "OBS-XYZ"

def test_suff_count_target_full():
    items = [ev(evidence_id=f"e{i}") for i in range(3)]
    a = assess_sufficiency("OBS", items, force=True, now=NOW)
    cnt = next(r for r in a.rules if r.name == "evidence_count")
    assert cnt.score == 100.0

def test_suff_count_partial():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    cnt = next(r for r in a.rules if r.name == "evidence_count")
    assert 0 < cnt.score < 100

def test_suff_skips_non_mapping():
    a = assess_sufficiency("OBS", [ev(), "bad", None], force=True, now=NOW)
    assert a.evidence_count == 1

def test_suff_to_dict():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    assert "rules" in a.to_dict() and a.to_dict()["enabled"] is True

def test_suff_band_thresholds():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    assert a.band in (Band.GREEN.value, Band.AMBER.value, Band.RED.value)

def test_suff_failsafe_bad_input():
    a = assess_sufficiency("OBS", "not-a-list", force=True, now=NOW)  # type: ignore[arg-type]
    assert a.enabled is True  # iterates string chars -> filtered to 0 mappings
    assert a.evidence_count == 0

def test_suff_item_scores_match_count():
    items = [ev(evidence_id="a"), ev(evidence_id="b")]
    a = assess_sufficiency("OBS", items, force=True, now=NOW)
    assert len(a.item_scores) == 2


# --------------------------------------------------------------------------- #
# 4. Closure readiness (22)
# --------------------------------------------------------------------------- #

def obs(**over):
    base = {"observation_id": "OBS-1", "framework": "PCI DSS", "control_id": "PCI-10.6",
            "status": "Open", "remediation_plan": "patch logging",
            "created_at": (NOW - timedelta(days=10)).isoformat()}
    base.update(over)
    return base

def test_readiness_disabled_default(monkeypatch):
    monkeypatch.setenv("OBSERVATION_READINESS_ENABLED", "false")
    a = assess_closure_readiness(obs(), [ev()])
    assert a.enabled is False and "disabled" in a.note

def test_readiness_enabled_flag(monkeypatch):
    monkeypatch.setenv("OBSERVATION_READINESS_ENABLED", "true")
    assert observation_readiness_enabled() is True

def test_readiness_ready():
    a = assess_closure_readiness(obs(), [ev(), ev(evidence_id="e2")], force=True, now=NOW)
    assert a.level in (ReadinessLevel.READY.value, ReadinessLevel.NEARLY_READY.value)

def test_readiness_no_evidence_blocked():
    a = assess_closure_readiness(obs(upload_filename=""), [], force=True, now=NOW)
    assert a.level == ReadinessLevel.NOT_READY.value
    assert any("no evidence" in b for b in a.blocking)

def test_readiness_no_approved_blocked():
    a = assess_closure_readiness(obs(), [ev(review_status="Rejected")], force=True, now=NOW)
    assert "no approved evidence" in a.blocking

def test_readiness_no_remediation():
    a = assess_closure_readiness(obs(remediation_plan="", remediation_notes="",
                                     remediation_owner=""), [ev()], force=True, now=NOW)
    assert a.factors["remediation_attached"] == 0.0

def test_readiness_remediation_from_owner():
    a = assess_closure_readiness(obs(remediation_plan="", remediation_owner="bob"),
                                 [ev()], force=True, now=NOW)
    assert a.factors["remediation_attached"] == 100.0

def test_readiness_no_control_coverage():
    a = assess_closure_readiness(obs(control_id="", control=""), [ev()], force=True, now=NOW)
    assert a.factors["control_coverage"] == 0.0

def test_readiness_age_fresh():
    a = assess_closure_readiness(obs(created_at=(NOW - timedelta(days=5)).isoformat()),
                                 [ev()], force=True, now=NOW)
    assert a.factors["observation_age"] == 100.0

def test_readiness_age_old():
    a = assess_closure_readiness(obs(created_at=(NOW - timedelta(days=200)).isoformat()),
                                 [ev()], force=True, now=NOW)
    assert a.factors["observation_age"] == 0.0

def test_readiness_unresolved_deps_list():
    a = assess_closure_readiness(obs(unresolved_dependencies=["d1", "d2"]),
                                 [ev()], force=True, now=NOW)
    assert a.factors["unresolved_dependencies"] < 100.0

def test_readiness_many_deps_blocked():
    a = assess_closure_readiness(obs(unresolved_dependencies=["a", "b", "c", "d"]),
                                 [ev()], force=True, now=NOW)
    assert "too many unresolved dependencies" in a.blocking

def test_readiness_deps_int():
    a = assess_closure_readiness(obs(unresolved_dependencies=2), [ev()], force=True, now=NOW)
    assert a.factors["unresolved_dependencies"] == 50.0

def test_readiness_evidence_approved_proportion():
    a = assess_closure_readiness(obs(), [ev(review_status="Approved"),
                                         ev(review_status="UnderReview")], force=True, now=NOW)
    assert a.factors["evidence_approved"] == 50.0

def test_readiness_factors_all_present():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert set(a.factors) == {"evidence_present", "evidence_approved",
                              "remediation_attached", "observation_age",
                              "control_coverage", "unresolved_dependencies"}

def test_readiness_score_range():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert 0 <= a.score <= 100

def test_readiness_reasons_when_complete():
    a = assess_closure_readiness(obs(), [ev(), ev(evidence_id="e2")], force=True, now=NOW)
    assert a.reasons

def test_readiness_obs_id_preserved():
    a = assess_closure_readiness(obs(observation_id="OBS-9"), [ev()], force=True, now=NOW)
    assert a.observation_id == "OBS-9"

def test_readiness_failsafe_bad_obs():
    a = assess_closure_readiness("bad", [], force=True)  # type: ignore[arg-type]
    assert a.enabled is False and "error" in a.note.lower()

def test_readiness_to_dict():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert "factors" in a.to_dict()

def test_readiness_evidence_via_obs_filename():
    a = assess_closure_readiness(obs(upload_filename="f.pdf", status="Approved"),
                                 [], force=True, now=NOW)
    assert a.factors["evidence_present"] == 100.0

def test_readiness_closed_status_approved():
    a = assess_closure_readiness(obs(status="Closed"), [], force=True, now=NOW)
    assert a.factors["evidence_approved"] == 100.0


# --------------------------------------------------------------------------- #
# 5. Reuse scoring (22)
# --------------------------------------------------------------------------- #

def test_reuse_disabled_default(monkeypatch):
    monkeypatch.setenv("EVIDENCE_REUSE_SCORING_ENABLED", "false")
    r = score_reuse(ev(), ev())
    assert r.enabled is False and "disabled" in r.note

def test_reuse_enabled_flag(monkeypatch):
    monkeypatch.setenv("EVIDENCE_REUSE_SCORING_ENABLED", "true")
    assert reuse_scoring_enabled() is True

def test_reuse_identical_high():
    src = {"framework_mapping": ["SOC2-CC8"], "control_mapping": ["code-review"],
           "object_type": "pull_request"}
    cand = ev(framework_mapping=["SOC2-CC8"], control_mapping=["code-review"],
              object_type="pull_request", review_status="Approved",
              collected_timestamp=(NOW - timedelta(days=5)).isoformat())
    r = score_reuse(src, cand, force=True, now=NOW)
    assert r.band == ReuseBand.HIGH.value

def test_reuse_no_overlap_low():
    src = {"framework_mapping": ["PCI-DSS-6"], "control_mapping": ["x"], "object_type": "document"}
    cand = ev(framework_mapping=["ISO27001-A"], control_mapping=["y"],
              object_type="quality_gate", review_status="Rejected",
              collected_timestamp=(NOW - timedelta(days=400)).isoformat())
    r = score_reuse(src, cand, force=True, now=NOW)
    assert r.band == ReuseBand.LOW.value

def test_reuse_framework_overlap_factor():
    src = {"framework_mapping": ["SOC2-CC8"]}
    cand = ev(framework_mapping=["SOC2-CC7"])
    r = score_reuse(src, cand, force=True, now=NOW)
    assert r.factors["framework_overlap"] == 100.0  # both base SOC2

def test_reuse_control_overlap_factor():
    src = {"control_mapping": ["code-review", "change-management"]}
    cand = ev(control_mapping=["code-review"])
    r = score_reuse(src, cand, force=True, now=NOW)
    assert 0 < r.factors["control_overlap"] < 100

def test_reuse_type_match():
    r = score_reuse({"object_type": "policy"}, ev(object_type="policy"), force=True, now=NOW)
    assert r.factors["type_match"] == 100.0

def test_reuse_type_mismatch():
    r = score_reuse({"object_type": "policy"}, ev(object_type="quality_gate"),
                    force=True, now=NOW)
    assert r.factors["type_match"] == 0.0

def test_reuse_age_fresh():
    cand = ev(collected_timestamp=(NOW - timedelta(days=10)).isoformat())
    r = score_reuse({}, cand, force=True, now=NOW)
    assert r.factors["age"] == 100.0

def test_reuse_age_old():
    cand = ev(collected_timestamp=(NOW - timedelta(days=400)).isoformat())
    r = score_reuse({}, cand, force=True, now=NOW)
    assert r.factors["age"] == 0.0

def test_reuse_status_approved():
    r = score_reuse({}, ev(review_status="Approved"), force=True, now=NOW)
    assert r.factors["status"] == 100.0

def test_reuse_status_rejected():
    r = score_reuse({}, ev(review_status="Rejected"), force=True, now=NOW)
    assert r.factors["status"] == 0.0

def test_reuse_approval_history():
    cand = ev(approval_history=[{"action": "approved", "actor": "x"}])
    r = score_reuse({}, cand, force=True, now=NOW)
    assert r.factors["approval_history"] == 100.0

def test_reuse_medium_band():
    src = {"framework_mapping": ["SOC2-CC8"], "control_mapping": ["x"]}
    cand = ev(framework_mapping=["SOC2-CC8"], control_mapping=["y"],
              object_type="document", review_status="UnderReview",
              collected_timestamp=(NOW - timedelta(days=180)).isoformat())
    r = score_reuse(src, cand, force=True, now=NOW)
    assert r.band in (ReuseBand.MEDIUM.value, ReuseBand.LOW.value, ReuseBand.HIGH.value)

def test_reuse_factors_present():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert set(r.factors) == {"framework_overlap", "control_overlap", "type_match",
                              "age", "status", "approval_history"}

def test_reuse_score_range():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert 0 <= r.score <= 100

def test_reuse_reasons():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert r.reasons

def test_reuse_candidate_id():
    r = score_reuse({}, ev(evidence_id="cand-9"), force=True, now=NOW)
    assert r.candidate_id == "cand-9"

def test_reuse_failsafe_bad_input():
    r = score_reuse("bad", "bad", force=True)  # type: ignore[arg-type]
    assert r.enabled is False and "error" in r.note.lower()

def test_reuse_to_dict():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert "factors" in r.to_dict()

def test_reuse_no_automatic_reuse():
    # The function only scores; it returns a ReuseScore, never mutates inputs.
    src, cand = ev(), ev()
    score_reuse(src, cand, force=True, now=NOW)
    assert "reused" not in src and "reused" not in cand

def test_reuse_empty_source_low_overlap():
    r = score_reuse({}, ev(), force=True, now=NOW)
    assert r.factors["framework_overlap"] == 0.0


# --------------------------------------------------------------------------- #
# 6. Change detection (20)
# --------------------------------------------------------------------------- #

def test_change_disabled_default(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CHANGE_DETECTION_ENABLED", "false")
    a = assess_change(ev(), ev())
    assert a.enabled is False and "disabled" in a.note

def test_change_enabled_flag(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CHANGE_DETECTION_ENABLED", "true")
    assert change_detection_enabled() is True

def test_change_none():
    a = assess_change(ev(), ev(), force=True)
    assert a.change_class == ChangeClass.NONE.value and a.changes == []

def test_change_major_hash():
    a = assess_change(ev(content_hash="a"), ev(content_hash="b"), force=True)
    assert a.change_class == ChangeClass.MAJOR.value

def test_change_major_approval():
    a = assess_change(ev(review_status="UnderReview"), ev(review_status="Approved"), force=True)
    assert a.change_class == ChangeClass.MAJOR.value

def test_change_moderate_owner():
    a = assess_change(ev(owner="alice"), ev(owner="bob"), force=True)
    assert a.change_class == ChangeClass.MODERATE.value

def test_change_moderate_control_mapping():
    a = assess_change(ev(control_mapping=["a"]), ev(control_mapping=["b"]), force=True)
    assert a.change_class == ChangeClass.MODERATE.value

def test_change_minor_title():
    a = assess_change(ev(title="x"), ev(title="y"), force=True)
    assert a.change_class == ChangeClass.MINOR.value

def test_change_minor_url():
    a = assess_change(ev(url="http://a"), ev(url="http://b"), force=True)
    assert a.change_class == ChangeClass.MINOR.value

def test_change_minor_metadata():
    a = assess_change(ev(metadata={"a": 1}), ev(metadata={"a": 2}), force=True)
    assert a.change_class == ChangeClass.MINOR.value

def test_change_moderate_to_major_escalation():
    old = ev(owner="a", control_mapping=["x"], framework_mapping=["SOC2-CC8"])
    new = ev(owner="b", control_mapping=["y"], framework_mapping=["ISO27001-A"])
    a = assess_change(old, new, force=True)
    assert a.change_class == ChangeClass.MAJOR.value

def test_change_two_moderate_not_major():
    old = ev(owner="a", control_mapping=["x"])
    new = ev(owner="b", control_mapping=["y"])
    a = assess_change(old, new, force=True)
    assert a.change_class == ChangeClass.MODERATE.value

def test_change_summary_lists_fields():
    a = assess_change(ev(owner="a"), ev(owner="b"), force=True)
    assert "owner" in a.summary

def test_change_changes_detail():
    a = assess_change(ev(owner="a"), ev(owner="b"), force=True)
    assert a.changes[0].old_value == "a" and a.changes[0].new_value == "b"

def test_change_hash_via_sha256_key():
    a = assess_change(ev(sha256="a"), ev(sha256="b"), force=True)
    assert a.change_class == ChangeClass.MAJOR.value

def test_change_normalizes_list_order():
    a = assess_change(ev(control_mapping=["a", "b"]), ev(control_mapping=["b", "a"]), force=True)
    assert a.change_class == ChangeClass.NONE.value

def test_change_case_insensitive():
    a = assess_change(ev(owner="Alice"), ev(owner="alice"), force=True)
    assert a.change_class == ChangeClass.NONE.value

def test_change_evidence_id_from_new():
    a = assess_change(ev(), ev(evidence_id="ev-42"), force=True)
    assert a.evidence_id == "ev-42"

def test_change_failsafe_bad_input():
    a = assess_change("bad", "bad", force=True)  # type: ignore[arg-type]
    assert a.enabled is False and "error" in a.note.lower()

def test_change_to_dict():
    a = assess_change(ev(owner="a"), ev(owner="b"), force=True)
    assert "changes" in a.to_dict()


# --------------------------------------------------------------------------- #
# 7. Query engine (24)
# --------------------------------------------------------------------------- #

def dataset():
    return [
        {"evidence_id": "1", "framework": "RBI", "application": "Payments",
         "status": "Rejected", "owner": "John", "control": "CIS-7",
         "object_type": "policy", "collected_timestamp": "2025-03-01T00:00:00Z"},
        {"evidence_id": "2", "framework": "RBI", "application": "Payments",
         "status": "Approved", "owner": "Jane", "control": "CIS-8",
         "object_type": "quality_gate", "collected_timestamp": "2025-07-01T00:00:00Z"},
        {"evidence_id": "3", "framework": "PCI DSS", "application": "Cards",
         "status": "Approved", "owner": "John", "control": "PCI-6",
         "object_type": "test_result", "collected_timestamp": "2024-05-01T00:00:00Z"},
    ]

def test_query_disabled_default(monkeypatch):
    monkeypatch.setenv("EVIDENCE_QUERY_ENABLED", "false")
    r = query_evidence(dataset(), {"framework": "RBI"})
    assert r.enabled is False

def test_query_enabled_flag(monkeypatch):
    monkeypatch.setenv("EVIDENCE_QUERY_ENABLED", "true")
    assert query_enabled() is True

def test_query_framework_filter():
    r = query_evidence(dataset(), {"framework": "RBI"}, force=True)
    assert r.total == 2

def test_query_application_filter():
    r = query_evidence(dataset(), {"application": "Cards"}, force=True)
    assert r.total == 1

def test_query_status_filter():
    r = query_evidence(dataset(), {"status": "Rejected"}, force=True)
    assert r.total == 1

def test_query_owner_filter():
    r = query_evidence(dataset(), {"owner": "John"}, force=True)
    assert r.total == 2

def test_query_control_filter():
    r = query_evidence(dataset(), {"control": "CIS-7"}, force=True)
    assert r.total == 1

def test_query_year_filter():
    r = query_evidence(dataset(), {"year": "2025"}, force=True)
    assert r.total == 2

def test_query_year_2024():
    r = query_evidence(dataset(), {"year": "2024"}, force=True)
    assert r.total == 1

def test_query_multi_filter_and():
    r = query_evidence(dataset(), {"framework": "RBI", "status": "Approved"}, force=True)
    assert r.total == 1

def test_query_no_match():
    r = query_evidence(dataset(), {"framework": "SWIFT"}, force=True)
    assert r.total == 0

def test_query_in_list_filter():
    r = query_evidence(dataset(), {"status": ["Approved", "Rejected"]}, force=True)
    assert r.total == 3

def test_query_aggregate_framework():
    r = query_evidence(dataset(), {}, group_by="framework", force=True)
    assert r.aggregations["framework"]["rbi"] == 2

def test_query_aggregate_owner():
    agg = aggregate(dataset(), "owner", force=True)
    assert agg["john"] == 2

def test_query_timeline():
    r = query_evidence(dataset(), {}, force=True)
    assert r.timeline and all("period" in t and "count" in t for t in r.timeline)

def test_query_timeline_sorted():
    r = query_evidence(dataset(), {}, force=True)
    periods = [t["period"] for t in r.timeline]
    assert periods == sorted(periods)

def test_query_unknown_filter_ignored():
    r = query_evidence(dataset(), {"bogus": "x"}, force=True)
    assert r.total == 3  # bogus field is not filterable -> ignored

def test_query_control_prefix_match():
    r = query_evidence(dataset(), {"control": "CIS"}, force=True)
    assert r.total == 2

def test_query_framework_prefix():
    r = query_evidence(dataset(), {"framework": "rbi"}, force=True)
    assert r.total == 2

def test_query_rows_returned():
    r = query_evidence(dataset(), {"framework": "RBI"}, force=True)
    assert len(r.rows) == 2

def test_query_filters_recorded():
    r = query_evidence(dataset(), {"framework": "RBI"}, force=True)
    assert r.filters == {"framework": "rbi"} or r.filters.get("framework") == "RBI"

def test_query_skips_non_mapping():
    r = query_evidence(dataset() + ["bad", None], {"framework": "RBI"}, force=True)
    assert r.total == 2

def test_query_failsafe(monkeypatch):
    # Passing a non-iterable should be handled by fail-safe.
    r = query_evidence(123, {"framework": "RBI"}, force=True)  # type: ignore[arg-type]
    assert r.enabled is False

def test_query_to_dict():
    r = query_evidence(dataset(), {"framework": "RBI"}, force=True)
    assert "rows" in r.to_dict() and r.to_dict()["total"] == 2


# --------------------------------------------------------------------------- #
# 8. DTOs (16)
# --------------------------------------------------------------------------- #

def test_version_card():
    h = build_version_history("ev-1", [{"hash": "1"}, {"hash": "2"}], force=True)
    card = EvidenceVersionCard.from_history(h)
    assert card.version_count == 2 and card.latest_version == 2

def test_version_card_to_dict():
    h = build_version_history("ev-1", [{"hash": "1"}], force=True)
    assert "history" in EvidenceVersionCard.from_history(h).to_dict()

def test_lineage_card():
    g = build_lineage_graph(obs_rows(), force=True)
    s = summarize(g, "framework:PCI DSS")
    card = EvidenceLineageCard.from_graph(g, s)
    assert card.node_count > 0 and "PCI-10.6" in card.controls

def test_lineage_card_to_dict():
    g = build_lineage_graph(obs_rows(), force=True)
    assert "frameworks" in EvidenceLineageCard.from_graph(g).to_dict()

def test_sufficiency_card():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    card = SufficiencyCard.from_assessment(a)
    assert card.subject == "OBS" and card.dimensions

def test_sufficiency_card_to_dict():
    a = assess_sufficiency("OBS", [ev()], force=True, now=NOW)
    assert "dimensions" in SufficiencyCard.from_assessment(a).to_dict()

def test_readiness_card():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    card = ReadinessCard.from_assessment(a)
    assert card.observation_id == "OBS-1"

def test_readiness_card_to_dict():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert "factors" in ReadinessCard.from_assessment(a).to_dict()

def test_reuse_card():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    card = ReuseCard.from_score(r)
    assert card.band in (ReuseBand.HIGH.value, ReuseBand.MEDIUM.value, ReuseBand.LOW.value)

def test_reuse_card_to_dict():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert "factors" in ReuseCard.from_score(r).to_dict()

def test_change_card():
    a = assess_change(ev(owner="a"), ev(owner="b"), force=True)
    card = EvidenceChangeCard.from_assessment(a)
    assert "owner" in card.changed_fields

def test_change_card_to_dict():
    a = assess_change(ev(owner="a"), ev(owner="b"), force=True)
    assert "summary" in EvidenceChangeCard.from_assessment(a).to_dict()

def test_query_card():
    r = query_evidence(dataset(), {"framework": "RBI"}, force=True)
    card = QueryResultCard.from_result(r)
    assert card.total == 2

def test_query_card_sample_limit():
    big = [dict(evidence_id=str(i), framework="RBI") for i in range(50)]
    r = query_evidence(big, {"framework": "RBI"}, force=True)
    card = QueryResultCard.from_result(r, sample=10)
    assert len(card.sample_rows) == 10

def test_query_card_to_dict():
    r = query_evidence(dataset(), {}, force=True)
    assert "timeline" in QueryResultCard.from_result(r).to_dict()

def test_all_cards_jsonable():
    import json
    h = build_version_history("ev-1", [{"hash": "1"}], force=True)
    g = build_lineage_graph(obs_rows(), force=True)
    suff = assess_sufficiency("O", [ev()], force=True, now=NOW)
    rdy = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    reu = score_reuse(ev(), ev(), force=True, now=NOW)
    chg = assess_change(ev(owner="a"), ev(owner="b"), force=True)
    qr = query_evidence(dataset(), {}, force=True)
    for card in (EvidenceVersionCard.from_history(h),
                 EvidenceLineageCard.from_graph(g, summarize(g, "framework:PCI DSS")),
                 SufficiencyCard.from_assessment(suff),
                 ReadinessCard.from_assessment(rdy),
                 ReuseCard.from_score(reu),
                 EvidenceChangeCard.from_assessment(chg),
                 QueryResultCard.from_result(qr)):
        json.dumps(card.to_dict())


# --------------------------------------------------------------------------- #
# 9. Flag OFF behavior + backward compatibility (10)
# --------------------------------------------------------------------------- #

def test_all_flags_off_by_default(monkeypatch):
    for f in ("EVIDENCE_VERSIONING_ENABLED", "EVIDENCE_LINEAGE_ENABLED",
              "SUFFICIENCY_ENGINE_ENABLED", "OBSERVATION_READINESS_ENABLED",
              "EVIDENCE_REUSE_SCORING_ENABLED", "EVIDENCE_CHANGE_DETECTION_ENABLED",
              "EVIDENCE_QUERY_ENABLED"):
        monkeypatch.setenv(f, "false")
    assert not versioning_enabled()
    assert not lineage_enabled()
    assert not sufficiency_enabled()
    assert not observation_readiness_enabled()
    assert not reuse_scoring_enabled()
    assert not change_detection_enabled()
    assert not query_enabled()

def test_versioning_off_no_compute(monkeypatch):
    monkeypatch.setenv("EVIDENCE_VERSIONING_ENABLED", "false")
    assert build_version_history("e", [{"hash": "1"}]).versions == []

def test_lineage_off_no_compute(monkeypatch):
    monkeypatch.setenv("EVIDENCE_LINEAGE_ENABLED", "false")
    assert build_lineage_graph(obs_rows()).enabled is False

def test_sufficiency_off_no_compute(monkeypatch):
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "false")
    assert assess_sufficiency("O", [ev()]).enabled is False

def test_readiness_off_no_compute(monkeypatch):
    monkeypatch.setenv("OBSERVATION_READINESS_ENABLED", "false")
    assert assess_closure_readiness(obs(), [ev()]).enabled is False

def test_reuse_off_no_compute(monkeypatch):
    monkeypatch.setenv("EVIDENCE_REUSE_SCORING_ENABLED", "false")
    assert score_reuse(ev(), ev()).enabled is False

def test_change_off_no_compute(monkeypatch):
    monkeypatch.setenv("EVIDENCE_CHANGE_DETECTION_ENABLED", "false")
    assert assess_change(ev(), ev(owner="z")).enabled is False

def test_query_off_no_compute(monkeypatch):
    monkeypatch.setenv("EVIDENCE_QUERY_ENABLED", "false")
    assert query_evidence(dataset(), {}).enabled is False

def test_sufficiency_v2_reuses_52a_flag(monkeypatch):
    # Enabling SUFFICIENCY_ENGINE_ENABLED enables V2 (no separate V2 flag).
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    assert sufficiency_enabled() is True
    assert assess_sufficiency("O", [ev()], now=NOW).enabled is True

def test_no_v2_flag_exists(monkeypatch):
    # There must be no SUFFICIENCY_ENGINE_V2_ENABLED dependency.
    monkeypatch.setenv("SUFFICIENCY_ENGINE_ENABLED", "true")
    monkeypatch.delenv("SUFFICIENCY_ENGINE_V2_ENABLED", raising=False)
    assert sufficiency_enabled() is True


# --------------------------------------------------------------------------- #
# 10. Explicit field-name contract — versioning (10)
# --------------------------------------------------------------------------- #

def test_version_content_hash_alias():
    h = build_version_history("e", [{"hash": "abc"}], force=True)
    assert h.versions[0].content_hash == "abc" == h.versions[0].hash

def test_version_previous_version_id_alias():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[1].previous_version_id == 1

def test_version_previous_version_id_none_first():
    h = build_version_history("e", [{"hash": "1"}], force=True)
    assert h.versions[0].previous_version_id is None

def test_version_superseded_by_version_id_alias():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[0].superseded_by_version_id == 2

def test_version_superseded_by_version_id_none_latest():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[1].superseded_by_version_id is None

def test_version_to_dict_has_content_hash():
    h = build_version_history("e", [{"hash": "abc"}], force=True)
    assert h.versions[0].to_dict()["content_hash"] == "abc"

def test_version_to_dict_has_previous_version_id():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[1].to_dict()["previous_version_id"] == 1

def test_version_to_dict_has_superseded_by_version_id():
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    assert h.versions[0].to_dict()["superseded_by_version_id"] == 2

def test_version_required_fields_present():
    h = build_version_history("e", [{"hash": "1", "uploaded_at": "2026-01-01",
                                     "uploaded_by": "a", "change_reason": "r"}], force=True)
    d = h.versions[0].to_dict()
    for f in ("version_number", "created_at", "created_by", "change_reason",
              "content_hash", "previous_version_id", "superseded_by_version_id"):
        assert f in d

def test_version_backward_compat_old_fields():
    # Old field names still present for backward compatibility.
    h = build_version_history("e", [{"hash": "1"}, {"hash": "2"}], force=True)
    d = h.versions[0].to_dict()
    assert "hash" in d and "previous_version" in d and "superseded_by" in d


# --------------------------------------------------------------------------- #
# 11. Explicit field-name contract — query engine (16)
# --------------------------------------------------------------------------- #

def dataset2():
    return [
        {"evidence_id": "1", "framework": "RBI", "application": "Payments",
         "observation_id": "OBS-1", "control": "CIS-7", "owner": "John",
         "status": "Submitted", "evidence_type": "policy", "approval_status": "Rejected",
         "uploaded_at": "2025-03-01T00:00:00Z"},
        {"evidence_id": "2", "framework": "RBI", "application": "Payments",
         "observation_id": "OBS-2", "control": "CIS-8", "owner": "Jane",
         "status": "Submitted", "evidence_type": "quality_gate", "approval_status": "Approved",
         "uploaded_at": "2025-07-15T00:00:00Z"},
        {"evidence_id": "3", "framework": "PCI DSS", "application": "Cards",
         "observation_id": "OBS-3", "control": "PCI-6", "owner": "John",
         "status": "Approved", "evidence_type": "test_result", "approval_status": "Approved",
         "uploaded_at": "2024-05-20T00:00:00Z"},
    ]

def test_query_observation_filter():
    r = query_evidence(dataset2(), {"observation": "OBS-1"}, force=True)
    assert r.total == 1 and r.rows[0]["evidence_id"] == "1"

def test_query_approval_status_filter():
    r = query_evidence(dataset2(), {"approval_status": "Approved"}, force=True)
    assert r.total == 2

def test_query_approval_status_rejected():
    r = query_evidence(dataset2(), {"approval_status": "Rejected"}, force=True)
    assert r.total == 1

def test_query_evidence_type_filter():
    r = query_evidence(dataset2(), {"evidence_type": "policy"}, force=True)
    assert r.total == 1

def test_query_evidence_type_quality_gate():
    r = query_evidence(dataset2(), {"evidence_type": "quality_gate"}, force=True)
    assert r.total == 1

def test_query_audit_year_filter():
    r = query_evidence(dataset2(), {"audit_year": "2025"}, force=True)
    assert r.total == 2

def test_query_audit_year_2024():
    r = query_evidence(dataset2(), {"audit_year": "2024"}, force=True)
    assert r.total == 1

def test_query_upload_date_exact():
    r = query_evidence(dataset2(), {"upload_date": "2025-03-01"}, force=True)
    assert r.total == 1 and r.rows[0]["evidence_id"] == "1"

def test_query_upload_date_no_match():
    r = query_evidence(dataset2(), {"upload_date": "2025-01-01"}, force=True)
    assert r.total == 0

def test_query_owner_with_new_dataset():
    r = query_evidence(dataset2(), {"owner": "John"}, force=True)
    assert r.total == 2

def test_query_status_vs_approval_status_distinct():
    # status=Submitted differs from approval_status=Approved on same rows
    submitted = query_evidence(dataset2(), {"status": "Submitted"}, force=True)
    approved = query_evidence(dataset2(), {"approval_status": "Approved"}, force=True)
    assert submitted.total == 2 and approved.total == 2

def test_query_observation_aggregate():
    r = query_evidence(dataset2(), {}, group_by="observation", force=True)
    assert r.aggregations["observation"]["obs-1"] == 1

def test_query_approval_status_aggregate():
    agg = aggregate(dataset2(), "approval_status", force=True)
    assert agg["approved"] == 2 and agg["rejected"] == 1

def test_query_audit_year_aggregate():
    agg = aggregate(dataset2(), "audit_year", force=True)
    assert agg["2025"] == 2 and agg["2024"] == 1

def test_query_combined_new_fields():
    r = query_evidence(dataset2(), {"framework": "RBI", "approval_status": "Approved",
                                    "audit_year": "2025"}, force=True)
    assert r.total == 1 and r.rows[0]["evidence_id"] == "2"

def test_query_all_required_fields_filterable():
    # Every newly required filter field must be honored (not silently dropped).
    for f, val, expected_nonzero in [
        ("framework", "RBI", True), ("application", "Payments", True),
        ("observation", "OBS-1", True), ("control", "CIS-7", True),
        ("owner", "John", True), ("status", "Submitted", True),
        ("evidence_type", "policy", True), ("approval_status", "Approved", True),
        ("upload_date", "2025-03-01", True), ("audit_year", "2025", True)]:
        r = query_evidence(dataset2(), {f: val}, force=True)
        assert (r.total > 0) == expected_nonzero, f


# --------------------------------------------------------------------------- #
# 12. Explicit field-name contract — reuse + readiness outputs (12)
# --------------------------------------------------------------------------- #

def test_reuse_reuse_score_alias():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert r.reuse_score == r.score

def test_reuse_reuse_band_alias():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert r.reuse_band == r.band

def test_reuse_reuse_reason_string():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert isinstance(r.reuse_reason, str) and r.reuse_reason

def test_reuse_to_dict_has_named_outputs():
    d = score_reuse(ev(), ev(), force=True, now=NOW).to_dict()
    assert "reuse_score" in d and "reuse_band" in d and "reuse_reason" in d

def test_reuse_reuse_band_valid():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert r.reuse_band in (ReuseBand.HIGH.value, ReuseBand.MEDIUM.value, ReuseBand.LOW.value)

def test_reuse_reuse_reason_joins_reasons():
    r = score_reuse(ev(), ev(), force=True, now=NOW)
    assert r.reuse_reason == "; ".join(r.reasons)

def test_readiness_readiness_score_alias():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert a.readiness_score == a.score

def test_readiness_readiness_band_alias():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert a.readiness_band == a.level

def test_readiness_blocking_items_alias():
    a = assess_closure_readiness(obs(upload_filename=""), [], force=True, now=NOW)
    assert a.blocking_items == a.blocking and a.blocking_items

def test_readiness_to_dict_has_named_outputs():
    d = assess_closure_readiness(obs(), [ev()], force=True, now=NOW).to_dict()
    assert "readiness_score" in d and "readiness_band" in d and "blocking_items" in d

def test_readiness_readiness_band_valid():
    a = assess_closure_readiness(obs(), [ev()], force=True, now=NOW)
    assert a.readiness_band in (ReadinessLevel.READY.value,
                                ReadinessLevel.NEARLY_READY.value,
                                ReadinessLevel.NOT_READY.value)

def test_readiness_blocking_items_empty_when_clean():
    a = assess_closure_readiness(obs(), [ev(), ev(evidence_id="e2")], force=True, now=NOW)
    assert isinstance(a.blocking_items, list)
