"""DNS validation module (Phase 5.3).

Deterministic DNS readiness assessment. With the default OFFLINE probe it performs
configuration validation only (is a hostname present/well-formed) and reports the
live-resolution outcome as UNKNOWN. A caller may inject a live DNSProbe to obtain
PASS/FAIL with resolved IP and latency.
"""

from __future__ import annotations

import re

from app.connectivity.models import DNSAssessment, Outcome
from app.connectivity.probes import DEFAULT_PROBE, DNSProbe

# Hostname per RFC 1123 (labels 1-63 chars, alnum + hyphen, no leading/trailing hyphen).
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*$"
)
_IPV4_RE = re.compile(r"^(\d{1,3})(\.\d{1,3}){3}$")


def is_valid_hostname(hostname: str) -> bool:
    if not hostname or not isinstance(hostname, str):
        return False
    host = hostname.strip()
    if host == "":
        return False
    if _IPV4_RE.match(host):
        return all(0 <= int(p) <= 255 for p in host.split("."))
    return bool(_HOSTNAME_RE.match(host))


def assess_dns(hostname: str, *, probe: DNSProbe | None = None) -> DNSAssessment:
    """Assess DNS readiness for a hostname. Never raises."""
    probe = probe or DEFAULT_PROBE
    host = (hostname or "").strip()

    if not host:
        return DNSAssessment(hostname="", outcome=Outcome.FAIL,
                             error_reason="no hostname configured")
    if not is_valid_hostname(host):
        return DNSAssessment(hostname=host, outcome=Outcome.FAIL,
                             error_reason="malformed hostname")

    # IP literal needs no resolution.
    if _IPV4_RE.match(host):
        return DNSAssessment(hostname=host, resolved_ip=host, latency_ms=0.0,
                             outcome=Outcome.PASS, error_reason="")

    try:
        result = probe.resolve(host) or {}
    except Exception as exc:  # noqa: BLE001 - probe must never break assessment
        return DNSAssessment(hostname=host, outcome=Outcome.UNKNOWN,
                             error_reason=f"probe error: {type(exc).__name__}")

    resolved_ip = str(result.get("resolved_ip", "") or "")
    error = str(result.get("error", "") or "")
    latency = result.get("latency_ms")

    if resolved_ip:
        return DNSAssessment(hostname=host, resolved_ip=resolved_ip,
                             latency_ms=latency, outcome=Outcome.PASS)
    # No IP and an explicit offline marker -> UNKNOWN (not a failure of config).
    if error:
        offline = "offline probe" in error.lower()
        return DNSAssessment(hostname=host, outcome=Outcome.UNKNOWN if offline else Outcome.FAIL,
                             latency_ms=latency, error_reason=error)
    return DNSAssessment(hostname=host, outcome=Outcome.UNKNOWN,
                         error_reason="no resolution result")
