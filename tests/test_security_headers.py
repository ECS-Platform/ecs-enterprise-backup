"""Security-headers middleware tests (production hardening / security review).

Verifies the app emits baseline security headers on its own (so non-proxied /
internal access is protected even without the nginx edge), that HSTS is TLS-only,
and that Content-Security-Policy stays opt-in via ECS_CSP (ECS templates use
inline styles/scripts). Fully offline.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_baseline_security_headers_present():
    r = client.get("/healthz")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert r.headers.get("X-Permitted-Cross-Domain-Policies") == "none"
    assert r.headers.get("Cross-Origin-Opener-Policy") == "same-origin"


def test_headers_present_on_api_route_too():
    r = client.get("/api/audit/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_hsts_absent_over_plain_http():
    # TestClient uses http:// — HSTS on plain HTTP is a spec violation.
    r = client.get("/healthz")
    assert "Strict-Transport-Security" not in r.headers


def test_hsts_present_when_forwarded_proto_https():
    r = client.get("/healthz", headers={"X-Forwarded-Proto": "https"})
    hsts = r.headers.get("Strict-Transport-Security", "")
    assert "max-age=" in hsts and "includeSubDomains" in hsts


def test_csp_is_opt_in():
    # Absent by default (inline styles/scripts would break under a strict CSP).
    r = client.get("/healthz")
    assert "Content-Security-Policy" not in r.headers


def test_csp_emitted_when_configured(monkeypatch):
    monkeypatch.setenv("ECS_CSP", "default-src 'self'")
    r = client.get("/healthz")
    assert r.headers.get("Content-Security-Policy") == "default-src 'self'"


def test_security_headers_do_not_break_request_id():
    # Regression: the new middleware must not disturb the existing X-Request-ID.
    r = client.get("/healthz")
    assert r.headers.get("X-Request-ID")


def test_security_headers_do_not_break_html_no_cache():
    # HTML pages keep their no-cache behavior alongside the new headers.
    r = client.get("/dashboard?role=owner&user=U")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    if r.headers.get("content-type", "").startswith("text/html"):
        assert "no-cache" in r.headers.get("Cache-Control", "")
