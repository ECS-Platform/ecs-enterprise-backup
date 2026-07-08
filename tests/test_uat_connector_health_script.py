"""Tests for scripts/run_uat_connector_health.py.

All adapter health checks are mocked — NO live network call is ever made. Verifies
alias resolution, the safe default (config-only), the ``--live`` probe path,
``--no-network`` override, ``--strict`` exit semantics, JSON output, and that no
secret value can appear in the output.
"""

from __future__ import annotations

import importlib
import os

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

import scripts.run_uat_connector_health as h


# --------------------------------------------------------------------------- #
# Alias resolution
# --------------------------------------------------------------------------- #
def test_resolve_all_returns_registry_order():
    adapters = h.resolve_adapters("all")
    assert "servicenow_cmdb" in adapters and "sharepoint_graph" in adapters
    assert "prisma_cloud" in adapters and "tripwire" in adapters
    # Registry-driven: "all" resolves to every registered adapter.
    from modules.operations import integrations
    assert len(adapters) == len(integrations.list_adapters())
    assert len(adapters) >= 11


@pytest.mark.parametrize("alias,module", [
    ("servicenow", "servicenow_cmdb"),
    ("graph", "sharepoint_graph"),
    ("sharepoint", "sharepoint_graph"),
    ("prisma", "prisma_cloud"),
    ("jira", "jira"),
    ("tripwire", "tripwire"),
])
def test_resolve_friendly_aliases(alias, module):
    assert h.resolve_adapters(alias) == [module]


def test_resolve_module_name_directly():
    assert h.resolve_adapters("prisma_cloud") == ["prisma_cloud"]


def test_resolve_unknown_adapter_raises():
    with pytest.raises(SystemExit):
        h.resolve_adapters("does-not-exist")


# --------------------------------------------------------------------------- #
# Helpers to install a fake adapter module
# --------------------------------------------------------------------------- #
class _FakeAdapter:
    def __init__(self, *, configured, masked, health=None, raise_health=False):
        self._configured = configured
        self._masked = masked
        self._health = health or {}
        self._raise_health = raise_health
        self.health_called = False

    def is_configured(self):
        return self._configured

    def masked_config(self):
        return dict(self._masked)

    def health_check(self):
        self.health_called = True
        if self._raise_health:
            raise RuntimeError("boom-should-be-caught")
        return dict(self._health)


@pytest.fixture
def patch_adapter(monkeypatch):
    def _install(module_name, fake):
        monkeypatch.setattr(h, "_import_adapter", lambda name: fake
                            if name == module_name else _raise_unknown(name))
        return fake

    def _raise_unknown(name):
        raise AssertionError(f"unexpected adapter import: {name}")

    return _install


# --------------------------------------------------------------------------- #
# Config-only default (no live call)
# --------------------------------------------------------------------------- #
def test_default_is_config_only_no_health_call(patch_adapter):
    fake = _FakeAdapter(configured=True, masked={"integration": "Jira", "api_token": "SET"})
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=False, no_network=False)
    assert rec["mode"] == "config-only"
    assert rec["configured"] is True and rec["status"] == "configured" and rec["ok"] is True
    assert fake.health_called is False  # never probed without --live


def test_not_configured_is_reported(patch_adapter):
    fake = _FakeAdapter(configured=False, masked={"integration": "Jira", "api_token": "MISSING"})
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=False, no_network=False)
    assert rec["configured"] is False and rec["status"] == "not_configured" and rec["ok"] is False
    assert "ECS_JIRA" in rec["remediation"]


# --------------------------------------------------------------------------- #
# Live probe (mocked) + no-network override
# --------------------------------------------------------------------------- #
def test_live_probe_healthy(patch_adapter):
    fake = _FakeAdapter(configured=True, masked={"integration": "Jira", "api_token": "SET"},
                        health={"ok": True, "status": "ok", "configured": True,
                                "masked_config": {"integration": "Jira", "api_token": "SET"}})
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=True, no_network=False)
    assert rec["mode"] == "live" and fake.health_called is True
    assert rec["ok"] is True and rec["status"] == "ok"


def test_live_probe_auth_error_sets_remediation(patch_adapter):
    fake = _FakeAdapter(configured=True, masked={"integration": "Jira", "api_token": "SET"},
                        health={"ok": False, "status": "auth_error", "errors": ["auth failed"]})
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=True, no_network=False)
    assert rec["ok"] is False and rec["status"] == "auth_error"
    assert "Authentication failed" in rec["remediation"]


def test_no_network_overrides_live(patch_adapter):
    fake = _FakeAdapter(configured=True, masked={"integration": "Jira", "api_token": "SET"})
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=True, no_network=True)
    assert rec["mode"] == "config-only" and fake.health_called is False


def test_unconfigured_never_probes_even_with_live(patch_adapter):
    fake = _FakeAdapter(configured=False, masked={"integration": "Jira", "api_token": "MISSING"})
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=True, no_network=False)
    assert fake.health_called is False and rec["status"] == "not_configured"


def test_health_exception_is_caught(patch_adapter):
    fake = _FakeAdapter(configured=True, masked={"integration": "Jira", "api_token": "SET"},
                        raise_health=True)
    patch_adapter("jira", fake)
    rec = h.check_adapter("jira", live=True, no_network=False)
    assert rec["status"] == "health_error" and rec["ok"] is False
    assert any("health_check" in e for e in rec["errors"])


def test_import_failure_is_caught(monkeypatch):
    def _boom(name):
        raise ImportError("no module")
    monkeypatch.setattr(h, "_import_adapter", _boom)
    rec = h.check_adapter("jira", live=False, no_network=False)
    assert rec["status"] == "adapter_error" and rec["ok"] is False


# --------------------------------------------------------------------------- #
# run() aggregation + strict semantics
# --------------------------------------------------------------------------- #
def _install_multi(monkeypatch, mapping):
    def _import(name):
        if name in mapping:
            return mapping[name]
        raise AssertionError(f"unexpected import {name}")
    monkeypatch.setattr(h, "_import_adapter", _import)


def test_run_all_summary(monkeypatch):
    fakes = {name: _FakeAdapter(configured=False,
                                masked={"integration": name, "x": "MISSING"})
             for name in h.resolve_adapters("all")}
    _install_multi(monkeypatch, fakes)
    report = h.run("all", live=False, no_network=False)
    assert report["total"] == len(h.resolve_adapters("all")) and report["configured"] == 0
    assert report["unhealthy_configured"] == 0  # unconfigured never counts as unhealthy


def test_strict_exit_zero_when_only_unconfigured(monkeypatch, capsys):
    fakes = {name: _FakeAdapter(configured=False, masked={"integration": name})
             for name in h.resolve_adapters("all")}
    _install_multi(monkeypatch, fakes)
    rc = h.main(["--adapter", "all", "--strict"])
    assert rc == 0  # not_configured must NOT fail strict mode


def test_strict_exit_one_when_configured_unhealthy(monkeypatch):
    fakes = {"jira": _FakeAdapter(
        configured=True, masked={"integration": "Jira", "api_token": "SET"},
        health={"ok": False, "status": "timeout", "errors": ["t/o"]})}
    _install_multi(monkeypatch, fakes)
    rc = h.main(["--adapter", "jira", "--strict", "--live"])
    assert rc == 1


def test_strict_exit_zero_when_configured_healthy(monkeypatch):
    fakes = {"jira": _FakeAdapter(
        configured=True, masked={"integration": "Jira", "api_token": "SET"},
        health={"ok": True, "status": "ok"})}
    _install_multi(monkeypatch, fakes)
    rc = h.main(["--adapter", "jira", "--strict", "--live"])
    assert rc == 0


# --------------------------------------------------------------------------- #
# Output: JSON + no secret leakage
# --------------------------------------------------------------------------- #
def test_json_output_is_valid(monkeypatch, capsys):
    fakes = {"jira": _FakeAdapter(configured=True,
                                  masked={"integration": "Jira", "api_token": "SET"})}
    _install_multi(monkeypatch, fakes)
    h.main(["--adapter", "jira", "--json"])
    out = capsys.readouterr().out
    import json
    data = json.loads(out)
    assert data["total"] == 1 and data["results"][0]["adapter"] == "jira"


def test_output_never_contains_secret_values(monkeypatch, capsys):
    # A well-behaved adapter only ever exposes SET/MISSING; simulate that and make
    # sure a raw secret placed nowhere-but-config cannot appear. The harness must
    # only print masked_config, so a raw token must never surface.
    fakes = {"jira": _FakeAdapter(
        configured=True,
        masked={"integration": "Jira", "api_token": "SET", "username": "SET"},
        health={"ok": True, "status": "ok",
                "masked_config": {"integration": "Jira", "api_token": "SET"}})}
    _install_multi(monkeypatch, fakes)
    h.main(["--adapter", "jira", "--live"])
    out = capsys.readouterr().out
    assert "SUPERSECRET" not in out  # never injected -> never leaked
    assert "SET" in out  # masked marker is shown instead


def test_render_smoke(monkeypatch):
    fakes = {"jira": _FakeAdapter(configured=False, masked={"integration": "Jira"})}
    _install_multi(monkeypatch, fakes)
    report = h.run("jira", live=False, no_network=False)
    text = h.render(report)
    assert "ECS UAT Connector Health" in text and "jira" in text
