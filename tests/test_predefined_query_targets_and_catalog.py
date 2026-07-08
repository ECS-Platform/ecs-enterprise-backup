"""Tests for the predefined-query target registry + catalog integrity.

Additive tests for this wave's deliverables (does not duplicate the existing
tests/test_predefined_*.py, which cover the engine/connectors/docker in depth):
  * catalog integrity (unique IDs; every control has framework + technology;
    supplementary controls are allow-list gated for live execution),
  * standalone target registries load (local/uat/prod/dr),
  * localhost allowed ONLY in the local registry (rejected in uat/prod/dr),
  * every target has the required fields + a known technology,
  * the docker-compose.predefined-queries.yml profiles load,
  * the runner script's inventory + validate-targets work offline.

Deterministic and offline (no live Docker/DB/network).
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from pathlib import Path

import pytest
import yaml

from config import predefined_query_target_registry as reg

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / "docker-compose.predefined-queries.yml"

DEPLOY_ENVS = ("local", "uat", "prod", "dr")
REMOTE_ENVS = ("uat", "prod", "dr")


# --------------------------------------------------------------------------- #
# Catalog integrity
# --------------------------------------------------------------------------- #
def _controls():
    from modules.operations.engines import predefined_queries_engine as engine

    engine.load_predefined_queries()
    return engine.get_all_controls()


def test_catalog_loads_nonempty():
    controls = _controls()
    assert len(controls) >= 150  # 187 today; guard against accidental emptiness


def test_no_duplicate_control_ids():
    ids = [c.get("control_id") for c in _controls()]
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate control_ids: {sorted(dupes)}"


def test_every_predefined_control_has_framework_and_technology():
    missing = []
    for c in _controls():
        if not c.get("predefined"):
            continue
        if not (c.get("frameworks") or c.get("framework_coverage")):
            missing.append((c.get("control_id"), "framework"))
        if not (c.get("technology") or "").strip():
            missing.append((c.get("control_id"), "technology"))
    assert not missing, f"controls missing framework/technology: {missing[:10]}"


def test_supplementary_controls_are_allowlist_gated():
    # Every supplementary control_id must appear in the engine's live allow-list
    # (SUPPLEMENTARY_QUERY_BY_ID), i.e. it has an exact query registered.
    from modules.operations.engines import supplementary_query_catalog as cat

    by_id = cat.SUPPLEMENTARY_QUERY_BY_ID
    for entry in cat.supplementary_controls():
        cid = entry["control_id"]
        assert cid in by_id and by_id[cid], f"{cid} not registered in allow-list"


def test_every_supplementary_control_has_validation_metadata():
    # Each supplementary entry carries query text + evidence_type (the validation
    # anchor) + a technology — the fields the execution/validation path relies on.
    from modules.operations.engines import supplementary_query_catalog as cat

    for e in cat.supplementary_controls():
        assert e.get("query"), f"{e['control_id']} has no query"
        assert e.get("evidence_type"), f"{e['control_id']} has no evidence_type"
        assert e.get("technology"), f"{e['control_id']} has no technology"


# --------------------------------------------------------------------------- #
# Target registries
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_registry_file_present_and_loads(env):
    assert reg.registry_path(env).is_file(), f"missing predefined_query_targets.{env}.yaml"
    data = reg.load_registry(env)
    assert data["environment"] == env
    assert isinstance(data["targets"], list) and data["targets"]


@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_registry_validates(env):
    rep = reg.validate_registry(env)
    assert rep.ok, rep.errors


@pytest.mark.parametrize("env", DEPLOY_ENVS)
def test_every_target_has_required_fields_and_known_tech(env):
    known_tech = {
        "postgresql", "yugabyte", "aurora_mysql", "oracle", "sqlserver", "mongodb",
        "linux", "nginx", "apache", "tomcat", "redis", "aerospike",
        "kubernetes", "openshift", "rhel8", "rhel9",
    }
    for t in reg.get_targets(env):
        for f in reg.REQUIRED_TARGET_FIELDS:
            assert t.get(f) not in (None, ""), f"{env}:{t.get('target_id')} missing {f}"
        assert t.get("technology") in known_tech, \
            f"{env}:{t.get('target_id')} unknown technology {t.get('technology')}"


def test_localhost_allowed_only_in_local():
    # local may reference localhost/loopback; validation passes.
    assert reg.validate_registry("local").ok
    local_hosts = " ".join(
        f"{t.get('hostname')} {t.get('ip')}" for t in reg.get_targets("local")
    ).lower()
    assert "localhost" in local_hosts or "127.0.0.1" in local_hosts


@pytest.mark.parametrize("env", REMOTE_ENVS)
def test_localhost_rejected_in_remote(env):
    # No remote registry may contain a localhost/loopback target...
    for t in reg.get_targets(env):
        for hf in ("hostname", "ip"):
            assert not reg._contains_localhost(t.get(hf)), \
                f"{env}:{t.get('target_id')} has localhost in {hf}"
    # ...and if one were injected, the validator must flag it.
    injected = {"environment": env, "targets": [{
        "target_id": "bad", "technology": "nginx", "hostname": "localhost", "ip": "127.0.0.1",
        "port": 443, "environment": env, "connector_ref": "nginx",
        "execution_method": "shell", "enabled": True,
    }]}
    import config.predefined_query_target_registry as m
    orig = m.load_registry
    m.load_registry = lambda e, _inj=injected: _inj if e == env else orig(e)
    try:
        rep = m.validate_registry(env)
    finally:
        m.load_registry = orig
    assert not rep.ok
    assert any("localhost" in e or "loopback" in e for e in rep.errors)


def test_remote_registries_have_no_inline_secrets():
    for env in REMOTE_ENVS:
        raw = reg.registry_path(env).read_text(encoding="utf-8").lower()
        # credentials must be referenced (credential_ref), not inlined.
        for marker in ("password:", "secret:", "token:", "api_key:"):
            assert marker not in raw, f"{env} registry contains inline secret field {marker!r}"


# --------------------------------------------------------------------------- #
# Docker compose profiles
# --------------------------------------------------------------------------- #
def test_predefined_queries_compose_loads_and_has_profiles():
    assert COMPOSE.is_file(), "docker-compose.predefined-queries.yml missing"
    data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = data.get("services") or {}
    assert services
    from collections import defaultdict

    prof = defaultdict(list)
    for name, svc in services.items():
        for p in (svc.get("profiles") or []):
            prof[p].append(name)
    for p in ("minimal", "standard", "extended"):
        assert prof[p], f"compose profile '{p}' has no services"
    # weight ordering: minimal ⊆ standard ⊆ extended
    assert len(prof["minimal"]) <= len(prof["standard"]) <= len(prof["extended"])


# --------------------------------------------------------------------------- #
# Runner script
# --------------------------------------------------------------------------- #
def test_runner_inventory_and_validate(tmp_path):
    import importlib

    runner = importlib.import_module("scripts.run_predefined_query_tests")
    # inventory to a temp path (do not clobber the committed doc in the test)
    import argparse

    rc = runner.cmd_inventory(argparse.Namespace(out=str(tmp_path / "inv.md")))
    assert rc == 0 and (tmp_path / "inv.md").is_file()
    text = (tmp_path / "inv.md").read_text(encoding="utf-8")
    assert "ECS Predefined Query Inventory" in text and "| Query ID |" in text
    # validate-targets --all should pass
    rc2 = runner.cmd_validate_targets(argparse.Namespace(env="all"))
    assert rc2 == 0
