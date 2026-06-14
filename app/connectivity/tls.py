"""TLS / certificate validation (Phase 5.3).

Deterministic TLS readiness assessment: certificate presence, expiry, chain
validity, and cipher/TLS-version compatibility. With the default OFFLINE probe no
certificate is fetched and the outcome is UNKNOWN. A caller may inject a live
TLSProbe returning a cert-info dict to obtain PASS/WARNING/FAIL.

Probe cert-info dict shape (all optional):
    {
      "present": bool,
      "expires_at": "ISO-8601",
      "chain_valid": bool,
      "cipher": str,
      "tls_version": "1.2" | "1.3" | ...,
      "error": str,
    }
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.connectivity.models import CertificateAssessment, Outcome
from app.connectivity.probes import DEFAULT_PROBE, TLSProbe


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _version_ok(found: str, minimum: str) -> bool:
    def parse(v: str) -> tuple[int, int]:
        v = str(v).strip().replace("TLSv", "").replace("TLS", "").strip()
        parts = v.split(".")
        try:
            return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        except (ValueError, IndexError):
            return (0, 0)
    return parse(found) >= parse(minimum)


def assess_tls(host: str, port: int = 443, *,
               warn_within_days: int = 30, min_tls_version: str = "1.2",
               now: datetime | None = None, probe: TLSProbe | None = None
               ) -> CertificateAssessment:
    """Assess TLS readiness for host:port. Never raises."""
    probe = probe or DEFAULT_PROBE
    now = now or datetime.now(timezone.utc)
    host = (host or "").strip()

    if not host:
        return CertificateAssessment(host="", outcome=Outcome.FAIL,
                                     error_reason="no host configured")

    try:
        info = probe.inspect(host, port) or {}
    except Exception as exc:  # noqa: BLE001
        return CertificateAssessment(host=host, outcome=Outcome.UNKNOWN,
                                     error_reason=f"probe error: {type(exc).__name__}")

    error = str(info.get("error", "") or "")
    if error and "offline probe" in error.lower():
        return CertificateAssessment(host=host, outcome=Outcome.UNKNOWN, error_reason=error)
    if error:
        return CertificateAssessment(host=host, outcome=Outcome.FAIL, error_reason=error)

    present = bool(info.get("present", False))
    if not present:
        return CertificateAssessment(host=host, present=False, outcome=Outcome.FAIL,
                                     error_reason="no certificate presented")

    expires_at = info.get("expires_at", "")
    chain_valid = info.get("chain_valid")
    cipher = str(info.get("cipher", "") or "")
    tls_version = str(info.get("tls_version", "") or "")

    days_to_expiry = None
    exp_dt = _parse_dt(expires_at)
    if exp_dt is not None:
        days_to_expiry = int((exp_dt - now).total_seconds() // 86400)

    outcome = Outcome.PASS
    reasons: list[str] = []

    if exp_dt is not None:
        if days_to_expiry is not None and days_to_expiry < 0:
            outcome = Outcome.FAIL
            reasons.append(f"certificate expired {abs(days_to_expiry)}d ago")
        elif days_to_expiry is not None and days_to_expiry <= warn_within_days:
            outcome = Outcome.WARNING
            reasons.append(f"certificate expires in {days_to_expiry}d")

    if chain_valid is False:
        outcome = Outcome.FAIL
        reasons.append("certificate chain invalid")

    if tls_version and not _version_ok(tls_version, min_tls_version):
        outcome = Outcome.FAIL
        reasons.append(f"TLS {tls_version} below minimum {min_tls_version}")

    return CertificateAssessment(
        host=host, present=True, expires_at=str(expires_at or ""),
        days_to_expiry=days_to_expiry, chain_valid=chain_valid,
        cipher=cipher, tls_version=tls_version, outcome=outcome,
        error_reason="; ".join(reasons),
    )
