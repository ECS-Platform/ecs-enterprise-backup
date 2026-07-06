"""Tests for the Observation Generation Engine (Milestone 3). Deterministic/offline."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.engines import observation_generation as obs
from modules.audit_intelligence.models import (
    OBS_STATUS_APPROVED,
    OBS_STATUS_CLOSED,
    OBS_STATUS_DRAFT,
    OBS_STATUS_REMEDIATED,
    OBS_STATUS_SUBMITTED,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    ValidationResult,
    VERDICT_FAIL,
    VERDICT_NOT_APPLICABLE,
    VERDICT_PASS,
    VERDICT_WARNING,
)


@pytest.fixture(autouse=True)
def _clean():
    obs.reset_observations()
    yield
    obs.reset_observations()


def _vr(**kw):
    base = dict(control_id="C", technology="NGINX", verdict=VERDICT_FAIL,
                control_status="Non-Compliant", rule_id="assertion.negative_signal",
                frameworks=("PCI DSS",), rationale="disabled")
    base.update(kw)
    return ValidationResult(**base)


# --------------------------------------------------------------------------- #
# Severity derivation
# --------------------------------------------------------------------------- #
def test_high_weight_assertion_fail_is_critical():
    assert obs.derive_severity(_vr(frameworks=("PCI DSS",), rule_id="assertion.negative_signal")) == SEVERITY_CRITICAL


def test_high_weight_or_assertion_fail_is_high():
    assert obs.derive_severity(_vr(frameworks=("PCI DSS",), rule_id="inventory.x")) == SEVERITY_HIGH
    assert obs.derive_severity(_vr(frameworks=("Custom",), rule_id="assertion.negative_signal")) == SEVERITY_HIGH


def test_plain_fail_is_medium():
    assert obs.derive_severity(_vr(frameworks=("Custom",), rule_id="inventory.x")) == SEVERITY_MEDIUM


def test_warning_severity():
    assert obs.derive_severity(_vr(verdict=VERDICT_WARNING, frameworks=("PCI DSS",))) == SEVERITY_MEDIUM
    assert obs.derive_severity(_vr(verdict=VERDICT_WARNING, frameworks=("Custom",))) == SEVERITY_LOW


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #
def test_generate_from_fail_creates_observation():
    o = obs.generate_observation(_vr(), asset_id="web-1", owner="Ops")
    assert o is not None
    assert o.severity == SEVERITY_CRITICAL
    assert o.status == OBS_STATUS_DRAFT
    assert o.asset_id == "web-1"
    assert o.recommendation and o.impact
    assert obs.get_observation(o.observation_id) is o


def test_pass_and_na_generate_nothing():
    assert obs.generate_observation(_vr(verdict=VERDICT_PASS)) is None
    assert obs.generate_observation(_vr(verdict=VERDICT_NOT_APPLICABLE)) is None


def test_generate_from_results_only_failures():
    results = [
        _vr(control_id="F1", verdict=VERDICT_FAIL),
        _vr(control_id="P1", verdict=VERDICT_PASS),
        _vr(control_id="W1", verdict=VERDICT_WARNING),
    ]
    made = obs.generate_from_results(results, asset_id="a")
    ids = {o.control_id for o in made}
    assert ids == {"F1", "W1"}


# --------------------------------------------------------------------------- #
# Workflow
# --------------------------------------------------------------------------- #
def test_valid_workflow_path():
    o = obs.generate_observation(_vr())
    obs.transition(o.observation_id, OBS_STATUS_SUBMITTED, user="a")
    obs.transition(o.observation_id, OBS_STATUS_APPROVED, user="mgr")
    obs.transition(o.observation_id, OBS_STATUS_REMEDIATED, user="eng")
    out = obs.transition(o.observation_id, OBS_STATUS_CLOSED, user="mgr")
    assert out.status == OBS_STATUS_CLOSED
    assert len(out.history) >= 5  # created + 4 transitions


def test_invalid_transition_raises():
    o = obs.generate_observation(_vr())
    with pytest.raises(obs.InvalidTransition):
        obs.transition(o.observation_id, OBS_STATUS_CLOSED)  # can't skip to closed


def test_transition_unknown_raises():
    with pytest.raises(KeyError):
        obs.transition("OBS-nope", OBS_STATUS_SUBMITTED)


# --------------------------------------------------------------------------- #
# Listing / summary
# --------------------------------------------------------------------------- #
def test_list_filters_and_summary():
    obs.generate_observation(_vr(control_id="A", frameworks=("PCI DSS",)))
    obs.generate_observation(_vr(control_id="B", verdict=VERDICT_WARNING, frameworks=("ISO27001",)))
    assert len(obs.list_observations()) == 2
    assert len(obs.list_observations(severity=SEVERITY_CRITICAL)) == 1
    assert len(obs.list_observations(framework="ISO27001")) == 1
    s = obs.summary()
    assert s["total"] == 2 and s["open"] == 2
