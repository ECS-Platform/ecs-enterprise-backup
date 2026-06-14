"""Network reachability validation (Phase 5.3).

Deterministic host/port/protocol reachability assessment for HTTPS, Database, and
File Share connectivity. With the default OFFLINE probe it validates the
host/port/protocol configuration and reports the live port check as UNKNOWN. A
caller may inject a live PortProbe to obtain PASS/FAIL.
"""

from __future__ import annotations

from app.connectivity.dns import is_valid_hostname
from app.connectivity.models import ConnectivityType, NetworkAssessment, Outcome
from app.connectivity.probes import DEFAULT_PROBE, PortProbe

# Map a connectivity/protocol label to a default port + canonical protocol name.
_PROTOCOL_DEFAULTS: dict[str, tuple[int, str]] = {
    "https": (443, "https"),
    "http": (80, "http"),
    "rest api": (443, "https"),
    "rest_api": (443, "https"),
    "soap api": (443, "https"),
    "soap_api": (443, "https"),
    "database": (5432, "tcp"),
    "file share": (445, "smb"),
    "file_share": (445, "smb"),
    "agent": (0, "agent"),
    "manual upload": (0, "manual"),
    "manual_upload": (0, "manual"),
}


def default_port_for(connectivity_type: str) -> int:
    key = str(connectivity_type or "").strip().lower()
    return _PROTOCOL_DEFAULTS.get(key, (0, ""))[0]


def protocol_for(connectivity_type: str) -> str:
    key = str(connectivity_type or "").strip().lower()
    return _PROTOCOL_DEFAULTS.get(key, (0, "tcp"))[1]


def assess_network(host: str, port: int = 0,
                   connectivity_type: ConnectivityType | str = "https",
                   *, probe: PortProbe | None = None) -> NetworkAssessment:
    """Assess network reachability for host:port. Never raises."""
    probe = probe or DEFAULT_PROBE
    ctype = connectivity_type.value if isinstance(connectivity_type, ConnectivityType) else str(connectivity_type)
    protocol = protocol_for(ctype)
    host = (host or "").strip()

    if port in (None, 0):
        port = default_port_for(ctype)

    # Agent / manual upload have no inbound network to assess -> PASS (N/A).
    if protocol in ("agent", "manual"):
        return NetworkAssessment(host=host, port=0, protocol=protocol,
                                 outcome=Outcome.PASS,
                                 error_reason=f"{protocol}: no network reachability required")

    if not host:
        return NetworkAssessment(host="", port=port, protocol=protocol,
                                 outcome=Outcome.FAIL, error_reason="no host configured")
    if not is_valid_hostname(host):
        return NetworkAssessment(host=host, port=port, protocol=protocol,
                                 outcome=Outcome.FAIL, error_reason="malformed host")
    if not isinstance(port, int) or port <= 0 or port > 65535:
        return NetworkAssessment(host=host, port=port, protocol=protocol,
                                 outcome=Outcome.FAIL, error_reason="invalid port")

    try:
        result = probe.check_port(host, port) or {}
    except Exception as exc:  # noqa: BLE001
        return NetworkAssessment(host=host, port=port, protocol=protocol,
                                 outcome=Outcome.UNKNOWN,
                                 error_reason=f"probe error: {type(exc).__name__}")

    is_open = result.get("open")
    latency = result.get("latency_ms")
    error = str(result.get("error", "") or "")

    if is_open is True:
        return NetworkAssessment(host=host, port=port, protocol=protocol,
                                 outcome=Outcome.PASS, latency_ms=latency)
    if is_open is False:
        return NetworkAssessment(host=host, port=port, protocol=protocol,
                                 outcome=Outcome.FAIL, latency_ms=latency,
                                 error_reason=error or "port closed/unreachable")
    # None -> not probed (offline) -> UNKNOWN
    return NetworkAssessment(host=host, port=port, protocol=protocol,
                             outcome=Outcome.UNKNOWN,
                             error_reason=error or "not probed")
