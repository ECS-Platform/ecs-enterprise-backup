"""Connectivity probe interfaces (Phase 5.3).

Defines the probe protocol used by DNS/network/TLS validators and an OFFLINE
default implementation that performs NO production network calls. The default
probe reports UNKNOWN for any live check; it exists so the entire framework runs
deterministically and safely without touching the network.

Callers who explicitly want live probing inject their own probe implementing the
same simple interface. ECS itself never wires a live probe in this phase.
"""

from __future__ import annotations

from typing import Any, Protocol


class DNSProbe(Protocol):
    def resolve(self, hostname: str) -> dict[str, Any]:
        """Return {'resolved_ip': str, 'latency_ms': float|None, 'error': str}."""
        ...


class PortProbe(Protocol):
    def check_port(self, host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
        """Return {'open': bool|None, 'latency_ms': float|None, 'error': str}."""
        ...


class TLSProbe(Protocol):
    def inspect(self, host: str, port: int = 443, timeout: float = 2.0) -> dict[str, Any]:
        """Return cert info dict or {'error': str}."""
        ...


class OfflineProbe:
    """Default probe. Performs no network I/O; every live check is UNKNOWN.

    This guarantees the assessment framework never makes production network calls
    unless a caller deliberately supplies a different probe.
    """

    OFFLINE_REASON = "offline probe (no network call performed)"

    def resolve(self, hostname: str) -> dict[str, Any]:
        return {"resolved_ip": "", "latency_ms": None, "error": self.OFFLINE_REASON}

    def check_port(self, host: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
        return {"open": None, "latency_ms": None, "error": self.OFFLINE_REASON}

    def inspect(self, host: str, port: int = 443, timeout: float = 2.0) -> dict[str, Any]:
        return {"error": self.OFFLINE_REASON}


# Module-level singleton default.
DEFAULT_PROBE = OfflineProbe()
