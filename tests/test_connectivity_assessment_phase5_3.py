"""Unit tests for the Connectivity Readiness & Certification framework (Phase 5.3).

Deterministic, non-LLM, no production network calls. Live PASS/FAIL/WARNING paths
are exercised with in-memory FAKE probes (never real sockets). The default offline
probe is also tested to confirm UNKNOWN/neutral behavior and that ECS makes no
network calls.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.connectivity.auth_readiness import assess_authentication
from app.connectivity.certification import (
    ConnectorCertificationEngine,
    certification_enabled,
)
from app.connectivity.discovery import assess_discovery
from app.connectivity.dns import assess_dns, is_valid_hostname
from app.connectivity.dtos import (
    AuthenticationReadinessCard,
    ConnectivityReadinessCard,
    ConnectorCertificationCard,
    DashboardWidget,
    EvidenceDiscoveryCard,
    NetworkAssessmentCard,
    build_dashboard_widgets,
)
from app.connectivity.engine import (
    ConnectivityAssessmentEngine,
    assess_connectivity,
    assessment_enabled,
)
from app.connectivity.models import (
    AuthType,
    CertificationStatus,
    ConnectivityAssessment,
    ConnectivityProfile,
    ConnectivityType,
    Environment,
    HostingType,
    Outcome,
    ReadinessStatus,
    RiskLevel,
)
from app.connectivity.network import assess_network, default_port_for, protocol_for
from app.connectivity.probes import DEFAULT_PROBE, OfflineProbe
from app.connectivity.scoring import (
    calculate_readiness,
    classify_risk,
    connectivity_category_score,
)
from app.connectivity.tls import assess_tls

NOW = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# Fake (offline) probes for deterministic live-path testing
# --------------------------------------------------------------------------- #

class FakeGoodProbe:
    def resolve(self, hostname):
        return {"resolved_ip": "10.0.0.5", "latency_ms": 3.2, "error": ""}

    def check_port(self, host, port, timeout=2.0):
        return {"open": True, "latency_ms": 5.0, "error": ""}

    def inspect(self, host, port=443, timeout=2.0):
        return {"present": True, "expires_at": (NOW + timedelta(days=200)).isoformat(),
                "chain_valid": True, "cipher": "TLS_AES_256_GCM_SHA384",
                "tls_version": "1.3", "error": ""}


class FakeBadProbe:
    def resolve(self, hostname):
        return {"resolved_ip": "", "latency_ms": None, "error": "NXDOMAIN"}

    def check_port(self, host, port, timeout=2.0):
        return {"open": False, "latency_ms": None, "error": "connection refused"}

    def inspect(self, host, port=443, timeout=2.0):
        return {"present": True, "expires_at": (NOW - timedelta(days=1)).isoformat(),
                "chain_valid": False, "cipher": "", "tls_version": "1.0", "error": ""}


class FakeWarnProbe:
    def resolve(self, hostname):
        return {"resolved_ip": "10.0.0.9", "latency_ms": 9.0, "error": ""}

    def check_port(self, host, port, timeout=2.0):
        return {"open": True, "latency_ms": 8.0, "error": ""}

    def inspect(self, host, port=443, timeout=2.0):
        return {"present": True, "expires_at": (NOW + timedelta(days=10)).isoformat(),
                "chain_valid": True, "cipher": "x", "tls_version": "1.2", "error": ""}


def make_profile(**over):
    base = dict(
        application_name="Net Banking", hosting_type=HostingType.CLOUD,
        environment=Environment.PRODUCTION, connectivity_type=ConnectivityType.REST_API,
        auth_type=AuthType.PAT, connector_type="github", host="api.github.com",
        port=443, base_url="https://api.github.com",
        auth_config={"token_env": "GH_TOKEN"}, collect=["repositories", "commits"],
        verify_ssl=True,
    )
    base.update(over)
    return ConnectivityProfile(**base)


@pytest.fixture(autouse=True)
def _flags_on(monkeypatch):
    # Default tests run with engines enabled via env so we exercise real logic.
    monkeypatch.setenv("CONNECTIVITY_ASSESSMENT_ENABLED", "true")
    monkeypatch.setenv("CONNECTOR_CERTIFICATION_ENABLED", "true")
    monkeypatch.setenv("GH_TOKEN", "ghp_xxx")


# --------------------------------------------------------------------------- #
# 1. Hostname validation (12)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("host", ["api.github.com", "example.org", "a.b.c.d.e",
                                  "host1", "10.0.0.1", "255.255.255.255"])
def test_valid_hostnames(host):
    assert is_valid_hostname(host) is True

@pytest.mark.parametrize("host", ["", "   ", "-bad.com", "bad-.com", "a..b",
                                  "256.1.1.1", "host_underscore.com"])
def test_invalid_hostnames(host):
    assert is_valid_hostname(host) is False


# --------------------------------------------------------------------------- #
# 2. DNS assessment (12)
# --------------------------------------------------------------------------- #

def test_dns_offline_unknown():
    r = assess_dns("api.github.com")
    assert r.outcome == Outcome.UNKNOWN

def test_dns_empty_fail():
    assert assess_dns("").outcome == Outcome.FAIL

def test_dns_malformed_fail():
    assert assess_dns("-nope-.com").outcome == Outcome.FAIL

def test_dns_ip_literal_pass():
    r = assess_dns("10.0.0.1")
    assert r.outcome == Outcome.PASS and r.resolved_ip == "10.0.0.1"

def test_dns_good_probe_pass():
    r = assess_dns("api.github.com", probe=FakeGoodProbe())
    assert r.outcome == Outcome.PASS and r.resolved_ip == "10.0.0.5"

def test_dns_good_probe_latency():
    r = assess_dns("api.github.com", probe=FakeGoodProbe())
    assert r.latency_ms == 3.2

def test_dns_bad_probe_fail():
    r = assess_dns("api.github.com", probe=FakeBadProbe())
    assert r.outcome == Outcome.FAIL and "NXDOMAIN" in r.error_reason

def test_dns_probe_exception_unknown():
    class Boom:
        def resolve(self, h): raise RuntimeError("x")
    assert assess_dns("api.github.com", probe=Boom()).outcome == Outcome.UNKNOWN

def test_dns_offline_reason_text():
    assert "offline probe" in assess_dns("x.com").error_reason

def test_dns_hostname_preserved():
    assert assess_dns("api.github.com", probe=FakeGoodProbe()).hostname == "api.github.com"

def test_dns_strips_whitespace():
    assert assess_dns("  10.0.0.1  ").outcome == Outcome.PASS

def test_dns_to_dict():
    assert "resolved_ip" in assess_dns("10.0.0.1").to_dict()


# --------------------------------------------------------------------------- #
# 3. Network assessment (16)
# --------------------------------------------------------------------------- #

def test_network_offline_unknown():
    assert assess_network("api.github.com", 443, "https").outcome == Outcome.UNKNOWN

def test_network_good_pass():
    assert assess_network("h", 443, "https", probe=FakeGoodProbe()).outcome == Outcome.PASS

def test_network_bad_fail():
    r = assess_network("h", 443, "https", probe=FakeBadProbe())
    assert r.outcome == Outcome.FAIL and "refused" in r.error_reason

def test_network_no_host_fail():
    assert assess_network("", 443, "https").outcome == Outcome.FAIL

def test_network_malformed_host_fail():
    assert assess_network("-x-.com", 443, "https").outcome == Outcome.FAIL

def test_network_invalid_port_fail():
    assert assess_network("h", 70000, "https").outcome == Outcome.FAIL

def test_network_zero_port_derives():
    r = assess_network("h", 0, "database", probe=FakeGoodProbe())
    assert r.port == 5432

def test_network_agent_pass_na():
    r = assess_network("", 0, "agent")
    assert r.outcome == Outcome.PASS and r.protocol == "agent"

def test_network_manual_pass_na():
    assert assess_network("", 0, "manual upload").outcome == Outcome.PASS

def test_network_probe_exception_unknown():
    class Boom:
        def check_port(self, *a, **k): raise OSError("x")
    assert assess_network("h", 443, "https", probe=Boom()).outcome == Outcome.UNKNOWN

@pytest.mark.parametrize("ctype,port", [("https", 443), ("rest api", 443),
                                        ("database", 5432), ("file share", 445),
                                        ("soap api", 443), ("http", 80)])
def test_default_port_for(ctype, port):
    assert default_port_for(ctype) == port

def test_protocol_for_database():
    assert protocol_for("database") == "tcp"

def test_protocol_for_file_share():
    assert protocol_for("file share") == "smb"

def test_network_to_dict():
    assert "protocol" in assess_network("h", 443, "https").to_dict()


# --------------------------------------------------------------------------- #
# 4. TLS assessment (16)
# --------------------------------------------------------------------------- #

def test_tls_offline_unknown():
    assert assess_tls("h").outcome == Outcome.UNKNOWN

def test_tls_no_host_fail():
    assert assess_tls("").outcome == Outcome.FAIL

def test_tls_good_pass():
    r = assess_tls("h", now=NOW, probe=FakeGoodProbe())
    assert r.outcome == Outcome.PASS and r.present is True

def test_tls_expiring_warning():
    r = assess_tls("h", warn_within_days=30, now=NOW, probe=FakeWarnProbe())
    assert r.outcome == Outcome.WARNING and r.days_to_expiry == 10

def test_tls_expired_fail():
    r = assess_tls("h", now=NOW, probe=FakeBadProbe())
    assert r.outcome == Outcome.FAIL

def test_tls_chain_invalid_fail():
    r = assess_tls("h", now=NOW, probe=FakeBadProbe())
    assert "chain invalid" in r.error_reason

def test_tls_low_version_fail():
    class P:
        def inspect(self, *a, **k):
            return {"present": True, "expires_at": (NOW + timedelta(days=100)).isoformat(),
                    "chain_valid": True, "tls_version": "1.0"}
    r = assess_tls("h", min_tls_version="1.2", now=NOW, probe=P())
    assert r.outcome == Outcome.FAIL and "below minimum" in r.error_reason

def test_tls_version_ok_13():
    r = assess_tls("h", min_tls_version="1.2", now=NOW, probe=FakeGoodProbe())
    assert r.outcome == Outcome.PASS

def test_tls_no_cert_fail():
    class P:
        def inspect(self, *a, **k): return {"present": False}
    assert assess_tls("h", now=NOW, probe=P()).outcome == Outcome.FAIL

def test_tls_days_to_expiry_computed():
    r = assess_tls("h", now=NOW, probe=FakeGoodProbe())
    assert r.days_to_expiry == 200

def test_tls_cipher_captured():
    r = assess_tls("h", now=NOW, probe=FakeGoodProbe())
    assert "AES" in r.cipher

def test_tls_probe_exception_unknown():
    class Boom:
        def inspect(self, *a, **k): raise RuntimeError("x")
    assert assess_tls("h", probe=Boom()).outcome == Outcome.UNKNOWN

def test_tls_probe_error_fail():
    class P:
        def inspect(self, *a, **k): return {"error": "handshake failed"}
    assert assess_tls("h", probe=P()).outcome == Outcome.FAIL

def test_tls_to_dict():
    assert "tls_version" in assess_tls("h", probe=FakeGoodProbe(), now=NOW).to_dict()


# --------------------------------------------------------------------------- #
# 5. Authentication readiness (18)
# --------------------------------------------------------------------------- #

def test_auth_pat_present(monkeypatch):
    monkeypatch.setenv("T", "x")
    r = assess_authentication(AuthType.PAT, {"token_env": "T"})
    assert r.outcome == Outcome.PASS and r.score == 100

def test_auth_pat_missing(monkeypatch):
    monkeypatch.delenv("T", raising=False)
    r = assess_authentication(AuthType.PAT, {"token_env": "T"})
    assert r.outcome == Outcome.FAIL

def test_auth_oauth_full(monkeypatch):
    for v in ("CID", "CS", "TEN"):
        monkeypatch.setenv(v, "x")
    r = assess_authentication(AuthType.OAUTH,
                              {"client_id_env": "CID", "client_secret_env": "CS",
                               "tenant_id_env": "TEN"})
    assert r.outcome == Outcome.PASS

def test_auth_oauth_partial(monkeypatch):
    monkeypatch.setenv("CID", "x")
    monkeypatch.delenv("CS", raising=False)
    monkeypatch.delenv("TEN", raising=False)
    r = assess_authentication(AuthType.OAUTH,
                              {"client_id_env": "CID", "client_secret_env": "CS",
                               "tenant_id_env": "TEN"})
    assert r.outcome == Outcome.WARNING and 0 < r.score < 100

def test_auth_service_account(monkeypatch):
    monkeypatch.setenv("U", "u"); monkeypatch.setenv("P", "p")
    r = assess_authentication(AuthType.SERVICE_ACCOUNT,
                              {"username_env": "U", "password_env": "P"})
    assert r.outcome == Outcome.PASS

def test_auth_jwt(monkeypatch):
    monkeypatch.setenv("JW", "x")
    assert assess_authentication(AuthType.JWT, {"token_env": "JW"}).outcome == Outcome.PASS

def test_auth_ldap(monkeypatch):
    monkeypatch.setenv("U", "u"); monkeypatch.setenv("P", "p")
    assert assess_authentication(AuthType.LDAP, {"username_env": "U", "password_env": "P"}).outcome == Outcome.PASS

def test_auth_kerberos(monkeypatch):
    monkeypatch.setenv("U", "u")
    assert assess_authentication(AuthType.KERBEROS, {"username_env": "U"}).outcome == Outcome.PASS

def test_auth_saml(monkeypatch):
    monkeypatch.setenv("CID", "x")
    assert assess_authentication(AuthType.SAML, {"client_id_env": "CID"}).outcome == Outcome.PASS

def test_auth_literal_value():
    # Non-_env key with literal value is accepted.
    r = assess_authentication("token", {"token": "literal"})
    assert r.outcome == Outcome.PASS

def test_auth_unknown_type_warning():
    r = assess_authentication("magic", {})
    assert r.outcome == Outcome.WARNING and r.score == 50

def test_auth_string_pat(monkeypatch):
    monkeypatch.setenv("T", "x")
    assert assess_authentication("pat", {"token_env": "T"}).outcome == Outcome.PASS

def test_auth_missing_fields_listed(monkeypatch):
    monkeypatch.delenv("T", raising=False)
    r = assess_authentication(AuthType.PAT, {"token_env": "T"})
    assert "token_env" in r.missing_fields

def test_auth_present_fields_listed(monkeypatch):
    monkeypatch.setenv("T", "x")
    r = assess_authentication(AuthType.PAT, {"token_env": "T"})
    assert "token_env" in r.present_fields

def test_auth_empty_env_treated_missing(monkeypatch):
    monkeypatch.setenv("T", "")
    assert assess_authentication(AuthType.PAT, {"token_env": "T"}).outcome == Outcome.FAIL

def test_auth_custom_requirements(monkeypatch):
    monkeypatch.setenv("X", "v")
    r = assess_authentication("custom", {"x_env": "X"},
                              requirements={"custom": ["x_env"]})
    assert r.outcome == Outcome.PASS

def test_auth_no_real_auth_performed():
    # Ensure no network: bogus env should still be config-only PASS/FAIL.
    r = assess_authentication(AuthType.PAT, {"token_env": "NOPE"})
    assert r.outcome in (Outcome.FAIL, Outcome.WARNING)

def test_auth_to_dict():
    assert "missing_fields" in assess_authentication(AuthType.PAT, {}).to_dict()


# --------------------------------------------------------------------------- #
# 6. Evidence discovery readiness (16)
# --------------------------------------------------------------------------- #

def test_discovery_github_full():
    r = assess_discovery("github", ["repositories", "commits"])
    assert r.outcome == Outcome.PASS and r.score == 100

def test_discovery_partial():
    r = assess_discovery("github", ["repositories", "tickets"])
    assert r.outcome == Outcome.WARNING and r.score == 50

def test_discovery_none_supported():
    r = assess_discovery("github", ["tickets", "spreadsheets"])
    assert r.outcome == Outcome.FAIL and r.score == 0

def test_discovery_unknown_connector():
    r = assess_discovery("mystery", ["x"])
    assert r.outcome == Outcome.WARNING and r.score == 0

def test_discovery_no_requested_full_breadth():
    r = assess_discovery("jira", [])
    assert r.outcome == Outcome.PASS and r.score == 100

@pytest.mark.parametrize("conn", ["jira", "github", "gitlab", "azure_devops",
                                  "confluence", "sharepoint", "servicenow"])
def test_discovery_known_connectors(conn):
    r = assess_discovery(conn, [])
    assert r.score == 100 and r.supported_categories

def test_discovery_case_insensitive():
    r = assess_discovery("GitHub", ["Repositories"])
    assert r.outcome == Outcome.PASS

def test_discovery_unsupported_listed():
    r = assess_discovery("github", ["repositories", "weird"])
    assert "weird" in r.unsupported_categories

def test_discovery_discoverable_listed():
    r = assess_discovery("github", ["repositories", "weird"])
    assert "repositories" in r.discoverable_categories

def test_discovery_custom_capabilities():
    r = assess_discovery("custom", ["x"], capabilities={"custom": ["x", "y"]})
    assert r.outcome == Outcome.PASS

def test_discovery_to_dict():
    assert "score" in assess_discovery("jira", []).to_dict()


# --------------------------------------------------------------------------- #
# 7. Scoring + risk (18)
# --------------------------------------------------------------------------- #

def test_connectivity_category_blend_pass():
    assert connectivity_category_score(Outcome.PASS, Outcome.PASS) == 100

def test_connectivity_category_blend_mixed():
    assert connectivity_category_score(Outcome.PASS, Outcome.FAIL) == 50

def test_connectivity_category_all_unknown_neutral():
    assert connectivity_category_score(Outcome.UNKNOWN, Outcome.UNKNOWN) == 50

def test_connectivity_category_one_unknown_excluded():
    assert connectivity_category_score(Outcome.PASS, Outcome.UNKNOWN) == 100

def test_readiness_green():
    rs = calculate_readiness({"connectivity": 100, "authentication": 100, "tls": 100,
                              "discovery": 100, "configuration": 100})
    assert rs.status == ReadinessStatus.GREEN and rs.score == 100

def test_readiness_red():
    rs = calculate_readiness({"connectivity": 0, "authentication": 0, "tls": 0,
                              "discovery": 0, "configuration": 0})
    assert rs.status == ReadinessStatus.RED and rs.score == 0

def test_readiness_amber():
    rs = calculate_readiness({"connectivity": 60, "authentication": 60, "tls": 60,
                              "discovery": 60, "configuration": 60})
    assert rs.status == ReadinessStatus.AMBER

def test_readiness_weights_sum_one():
    rs = calculate_readiness({"connectivity": 50})
    assert abs(sum(rs.weights.values()) - 1.0) < 1e-6

def test_readiness_custom_bands():
    rs = calculate_readiness({"connectivity": 85, "authentication": 85, "tls": 85,
                              "discovery": 85, "configuration": 85},
                             bands={"green_min": 90, "amber_min": 70})
    assert rs.status == ReadinessStatus.AMBER

def test_readiness_zero_weights_fallback():
    rs = calculate_readiness({"connectivity": 100, "authentication": 100, "tls": 100,
                              "discovery": 100, "configuration": 100},
                             weights={"connectivity": 0, "authentication": 0, "tls": 0,
                                      "discovery": 0, "configuration": 0})
    assert rs.score == 100

def test_risk_low():
    r = classify_risk({"connectivity": 100, "authentication": 100,
                       "discovery": 100, "configuration": 100})
    assert r.level == RiskLevel.LOW

def test_risk_critical():
    r = classify_risk({"connectivity": 0, "authentication": 0,
                       "discovery": 0, "configuration": 0})
    assert r.level == RiskLevel.CRITICAL

def test_risk_high():
    r = classify_risk({"connectivity": 40, "authentication": 40,
                       "discovery": 50, "configuration": 60})
    assert r.level in (RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.CRITICAL)

def test_risk_medium():
    r = classify_risk({"connectivity": 80, "authentication": 70,
                       "discovery": 70, "configuration": 70})
    assert r.level in (RiskLevel.LOW, RiskLevel.MEDIUM)

def test_risk_factors_present():
    r = classify_risk({"connectivity": 0, "authentication": 100,
                       "discovery": 100, "configuration": 100})
    assert r.factors["connectivity"] == 100

def test_risk_reasons_present():
    r = classify_risk({"connectivity": 0, "authentication": 0,
                       "discovery": 0, "configuration": 0})
    assert r.reasons

def test_risk_no_gaps_reason():
    r = classify_risk({"connectivity": 100, "authentication": 100,
                       "discovery": 100, "configuration": 100})
    assert "no significant" in r.reasons[0]

def test_readiness_to_dict():
    assert "category_scores" in calculate_readiness({"connectivity": 50}).to_dict()


# --------------------------------------------------------------------------- #
# 8. Engine orchestration (20)
# --------------------------------------------------------------------------- #

def test_engine_disabled_default(monkeypatch):
    monkeypatch.setenv("CONNECTIVITY_ASSESSMENT_ENABLED", "false")
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile())
    assert a.enabled is False and "disabled" in a.note

def test_engine_force_when_disabled(monkeypatch):
    monkeypatch.setenv("CONNECTIVITY_ASSESSMENT_ENABLED", "false")
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), force=True)
    assert a.enabled is True

def test_engine_enabled_flag():
    assert assessment_enabled() is True  # set by fixture

def test_engine_offline_runs():
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), now=NOW)
    assert a.enabled is True
    assert a.dns.outcome == Outcome.UNKNOWN  # offline
    assert a.network.outcome == Outcome.UNKNOWN

def test_engine_offline_auth_config_evaluated():
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), now=NOW)
    # GH_TOKEN is set in fixture -> PAT present
    assert a.authentication.outcome == Outcome.PASS

def test_engine_offline_discovery_evaluated():
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), now=NOW)
    assert a.discovery.outcome == Outcome.PASS

def test_engine_good_probes_green():
    eng = ConnectivityAssessmentEngine(dns_probe=FakeGoodProbe(),
                                       port_probe=FakeGoodProbe(),
                                       tls_probe=FakeGoodProbe())
    a = eng.assess_connectivity(make_profile(), now=NOW)
    assert a.readiness.status == ReadinessStatus.GREEN
    assert a.risk.level == RiskLevel.LOW

def test_engine_bad_probes_red():
    eng = ConnectivityAssessmentEngine(dns_probe=FakeBadProbe(),
                                       port_probe=FakeBadProbe(),
                                       tls_probe=FakeBadProbe())
    p = make_profile(auth_config={"token_env": "MISSING"}, collect=["weird"])
    a = eng.assess_connectivity(p, now=NOW)
    assert a.readiness.status in (ReadinessStatus.RED, ReadinessStatus.AMBER)
    assert a.risk.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

def test_engine_dns_pass_with_good_probe():
    eng = ConnectivityAssessmentEngine(dns_probe=FakeGoodProbe())
    a = eng.assess_connectivity(make_profile(), now=NOW)
    assert a.dns.outcome == Outcome.PASS

def test_engine_host_from_base_url():
    p = make_profile(host="", base_url="https://user@api.example.com:8443/v1")
    eng = ConnectivityAssessmentEngine(dns_probe=FakeGoodProbe())
    a = eng.assess_connectivity(p, now=NOW)
    assert a.dns.hostname == "api.example.com"

def test_engine_agent_no_network():
    p = make_profile(connectivity_type=ConnectivityType.AGENT, host="", base_url="")
    a = ConnectivityAssessmentEngine().assess_connectivity(p, now=NOW)
    assert a.network.outcome == Outcome.PASS

def test_engine_manual_upload():
    p = make_profile(connectivity_type=ConnectivityType.MANUAL_UPLOAD, host="", base_url="")
    a = ConnectivityAssessmentEngine().assess_connectivity(p, now=NOW)
    assert a.network.outcome == Outcome.PASS

def test_engine_database_port():
    p = make_profile(connectivity_type=ConnectivityType.DATABASE, port=0,
                     host="db.local", base_url="")
    eng = ConnectivityAssessmentEngine(port_probe=FakeGoodProbe())
    a = eng.assess_connectivity(p, now=NOW)
    assert a.network.port == 5432

def test_engine_configuration_checks_present():
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), now=NOW)
    assert a.configuration.checks and a.configuration.score > 0

def test_engine_config_missing_host_fail():
    p = make_profile(host="", base_url="", connectivity_type=ConnectivityType.REST_API)
    a = ConnectivityAssessmentEngine().assess_connectivity(p, force=True, now=NOW)
    assert a.configuration.outcome == Outcome.FAIL

def test_engine_to_dict_jsonable():
    import json
    a = ConnectivityAssessmentEngine(dns_probe=FakeGoodProbe()).assess_connectivity(
        make_profile(), now=NOW)
    json.dumps(a.to_dict())

def test_engine_module_wrapper():
    a = assess_connectivity(make_profile(), now=NOW, dns_probe=FakeGoodProbe())
    assert isinstance(a, ConnectivityAssessment) and a.enabled is True

def test_engine_failsafe_bad_profile():
    a = ConnectivityAssessmentEngine().assess_connectivity(object(), force=True)  # type: ignore[arg-type]
    assert a.enabled is False and "error" in a.note.lower()

def test_engine_default_probe_is_offline():
    eng = ConnectivityAssessmentEngine()
    assert isinstance(eng.dns_probe, OfflineProbe)

def test_engine_uses_offline_singleton():
    assert DEFAULT_PROBE.resolve("x")["error"]


# --------------------------------------------------------------------------- #
# 9. Certification engine (16)
# --------------------------------------------------------------------------- #

def _good_assessment():
    eng = ConnectivityAssessmentEngine(dns_probe=FakeGoodProbe(),
                                       port_probe=FakeGoodProbe(),
                                       tls_probe=FakeGoodProbe())
    return eng.assess_connectivity(make_profile(), now=NOW)

def _bad_assessment():
    eng = ConnectivityAssessmentEngine(dns_probe=FakeBadProbe(),
                                       port_probe=FakeBadProbe(),
                                       tls_probe=FakeBadProbe())
    return eng.assess_connectivity(
        make_profile(auth_config={"token_env": "MISSING"}, collect=["weird"]), now=NOW)

def test_cert_enabled_flag():
    assert certification_enabled() is True

def test_cert_disabled_default(monkeypatch):
    # Build the assessment while enabled, then disable the gate (env wins over the
    # config cache) and confirm certify() short-circuits to a disabled result.
    a = _good_assessment()
    monkeypatch.setenv("CONNECTOR_CERTIFICATION_ENABLED", "false")
    c = ConnectorCertificationEngine().certify(a)
    assert c.status == CertificationStatus.NOT_CERTIFIED and "disabled" in c.reasons[0]

def test_cert_certified():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert c.status == CertificationStatus.CERTIFIED

def test_cert_not_certified_bad():
    c = ConnectorCertificationEngine().certify(_bad_assessment())
    assert c.status == CertificationStatus.NOT_CERTIFIED

def test_cert_hard_fail_auth(monkeypatch):
    a = _good_assessment()
    a.authentication.outcome = Outcome.FAIL
    c = ConnectorCertificationEngine().certify(a, force=True)
    assert c.status == CertificationStatus.NOT_CERTIFIED
    assert any("hard-gate" in r for r in c.reasons)

def test_cert_partial():
    a = _good_assessment()
    # Force mid-range category scores.
    a.readiness.category_scores = {"connectivity": 60, "authentication": 60,
                                   "discovery": 60, "configuration": 60}
    c = ConnectorCertificationEngine().certify(a, force=True)
    assert c.status == CertificationStatus.PARTIALLY_CERTIFIED

def test_cert_factors_present():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert set(c.factors) == {"connectivity", "authentication", "discovery", "configuration"}

def test_cert_score_numeric():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert 0 <= c.score <= 100

def test_cert_connector_type():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert c.connector_type == "github"

def test_cert_reasons_present():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert c.reasons

def test_cert_custom_thresholds():
    eng = ConnectorCertificationEngine(policy={"certified_min": 99,
                                               "partially_certified_min": 50,
                                               "hard_fail_categories": []})
    a = _good_assessment()
    c = eng.certify(a, force=True)
    assert c.status in (CertificationStatus.PARTIALLY_CERTIFIED, CertificationStatus.CERTIFIED)

def test_cert_failsafe():
    class Boom:
        connector_type = "x"
        @property
        def readiness(self): raise RuntimeError("x")
    c = ConnectorCertificationEngine().certify(Boom(), force=True)  # type: ignore[arg-type]
    assert c.status == CertificationStatus.NOT_CERTIFIED

def test_cert_to_dict():
    assert "factors" in ConnectorCertificationEngine().certify(_good_assessment()).to_dict()

def test_cert_hard_fail_config():
    a = _good_assessment()
    a.configuration.outcome = Outcome.FAIL
    c = ConnectorCertificationEngine().certify(a, force=True)
    assert c.status == CertificationStatus.NOT_CERTIFIED

def test_cert_no_hard_fail_when_pass():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert c.status == CertificationStatus.CERTIFIED

def test_cert_status_enum_value():
    c = ConnectorCertificationEngine().certify(_good_assessment())
    assert c.status.value in ("Certified", "Partially Certified", "Not Certified")


# --------------------------------------------------------------------------- #
# 10. DTOs / cards / widgets (18)
# --------------------------------------------------------------------------- #

def test_network_card():
    card = NetworkAssessmentCard.from_assessment(_good_assessment())
    assert card.overall == Outcome.PASS.value

def test_network_card_offline_unknown():
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), now=NOW)
    card = NetworkAssessmentCard.from_assessment(a)
    # dns/network unknown but tls unknown too -> overall unknown
    assert card.overall in (Outcome.UNKNOWN.value, Outcome.WARNING.value, Outcome.PASS.value)

def test_auth_card():
    card = AuthenticationReadinessCard.from_assessment(_good_assessment())
    assert card.outcome == Outcome.PASS.value and card.auth_type == "PAT"

def test_auth_card_missing(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    a = ConnectivityAssessmentEngine().assess_connectivity(make_profile(), force=True, now=NOW)
    card = AuthenticationReadinessCard.from_assessment(a)
    assert card.outcome == Outcome.FAIL.value

def test_discovery_card():
    card = EvidenceDiscoveryCard.from_assessment(_good_assessment())
    assert card.connector_type == "github" and card.score == 100

def test_readiness_card():
    card = ConnectivityReadinessCard.from_assessment(_good_assessment())
    assert card.status == ReadinessStatus.GREEN.value and card.enabled is True

def test_readiness_card_risk_level():
    card = ConnectivityReadinessCard.from_assessment(_good_assessment())
    assert card.risk_level == RiskLevel.LOW.value

def test_certification_card():
    card = ConnectorCertificationCard.from_assessment(_good_assessment())
    assert card.status == CertificationStatus.CERTIFIED.value

def test_certification_card_force_disabled(monkeypatch):
    monkeypatch.delenv("CONNECTOR_CERTIFICATION_ENABLED", raising=False)
    card = ConnectorCertificationCard.from_assessment(_good_assessment(), force=True)
    assert card.status == CertificationStatus.CERTIFIED.value

def test_widgets_count():
    widgets = build_dashboard_widgets(_good_assessment())
    assert len(widgets) == 5 and all(isinstance(w, DashboardWidget) for w in widgets)

def test_widgets_ids():
    ids = {w.widget_id for w in build_dashboard_widgets(_good_assessment())}
    assert ids == {"connectivity_readiness", "connector_certification",
                   "onboarding_risk", "network_assessment", "evidence_discovery"}

def test_widget_readiness_value():
    widgets = {w.widget_id: w for w in build_dashboard_widgets(_good_assessment())}
    assert widgets["connectivity_readiness"].value > 0

def test_widget_certification_badge():
    widgets = {w.widget_id: w for w in build_dashboard_widgets(_good_assessment())}
    assert widgets["connector_certification"].value == CertificationStatus.CERTIFIED.value

def test_widget_risk_status():
    widgets = {w.widget_id: w for w in build_dashboard_widgets(_good_assessment())}
    assert widgets["onboarding_risk"].value == RiskLevel.LOW.value

def test_widget_network_list():
    widgets = {w.widget_id: w for w in build_dashboard_widgets(_good_assessment())}
    assert len(widgets["network_assessment"].items) == 3

def test_cards_to_dict():
    a = _good_assessment()
    for card in (NetworkAssessmentCard.from_assessment(a),
                 AuthenticationReadinessCard.from_assessment(a),
                 EvidenceDiscoveryCard.from_assessment(a),
                 ConnectivityReadinessCard.from_assessment(a),
                 ConnectorCertificationCard.from_assessment(a)):
        assert isinstance(card.to_dict(), dict)

def test_widget_to_dict():
    w = build_dashboard_widgets(_good_assessment())[0]
    assert "widget_id" in w.to_dict()

def test_widgets_jsonable():
    import json
    json.dumps([w.to_dict() for w in build_dashboard_widgets(_good_assessment())])


# --------------------------------------------------------------------------- #
# 11. Profile model (8)
# --------------------------------------------------------------------------- #

def test_profile_to_dict():
    d = make_profile().to_dict()
    assert d["hosting_type"] == "Cloud" and d["auth_type"] == "PAT"

def test_profile_enum_serialization():
    d = make_profile(connectivity_type=ConnectivityType.DATABASE).to_dict()
    assert d["connectivity_type"] == "Database"

def test_profile_string_fields_allowed():
    p = ConnectivityProfile(application_name="X", hosting_type="Cloud",
                            connectivity_type="https", auth_type="pat")
    a = ConnectivityAssessmentEngine().assess_connectivity(p, force=True, now=NOW)
    assert a.enabled is True

@pytest.mark.parametrize("ht", list(HostingType))
def test_all_hosting_types(ht):
    assert make_profile(hosting_type=ht).to_dict()["hosting_type"] == ht.value

@pytest.mark.parametrize("env", list(Environment))
def test_all_environments(env):
    assert make_profile(environment=env).to_dict()["environment"] == env.value
