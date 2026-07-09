"""Lightweight runtime telemetry for the ECS infrastructure benchmark (PART 1).

Captures CPU / memory / disk / network / timing around a block of work using
ONLY optional stdlib + optional ``psutil`` — degrading gracefully to whatever is
available (never raising, never adding a hard dependency).

Usage::

    from benchmarks.capacity.telemetry import RuntimeTelemetry

    with RuntimeTelemetry("phase1-estimate") as t:
        ... work ...
    data = t.result           # JSON-serializable dict
    t.add_step("retrieve")    # optional per-step timing markers

Availability is reported in ``result["available"]`` so consumers know which
metrics are real vs unavailable on this host.
"""

from __future__ import annotations

import time
from typing import Any, Optional

# ---- optional imports (all degrade gracefully) ----
try:  # process metrics
    import psutil  # type: ignore
    _HAVE_PSUTIL = True
except Exception:  # noqa: BLE001
    psutil = None  # type: ignore
    _HAVE_PSUTIL = False

try:  # unix rusage (max RSS, CPU time)
    import resource  # type: ignore
    _HAVE_RESOURCE = True
except Exception:  # noqa: BLE001
    resource = None  # type: ignore
    _HAVE_RESOURCE = False

try:  # python heap tracking
    import tracemalloc  # type: ignore
    _HAVE_TRACEMALLOC = True
except Exception:  # noqa: BLE001
    tracemalloc = None  # type: ignore
    _HAVE_TRACEMALLOC = False


def _round(x: Any, n: int = 3) -> Optional[float]:
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return None


def telemetry_availability() -> dict[str, bool]:
    """Which telemetry backends are available on this host."""
    return {
        "psutil": _HAVE_PSUTIL,
        "resource": _HAVE_RESOURCE,
        "tracemalloc": _HAVE_TRACEMALLOC,
    }


class RuntimeTelemetry:
    """Context manager capturing runtime telemetry around a block. Never raises.

    All captured values are JSON-serializable primitives; metrics that cannot be
    read on the current host are reported as ``None`` and listed under
    ``available``.
    """

    def __init__(self, name: str = "benchmark", *, trace_python_heap: bool = False):
        self.name = name
        self.trace_python_heap = trace_python_heap and _HAVE_TRACEMALLOC
        self.result: dict[str, Any] = {"name": name, "available": telemetry_availability()}
        self._t0 = 0.0
        self._proc = None
        self._cpu_times0 = None
        self._io0 = None
        self._net0 = None
        self._started_tracemalloc = False

    # ---- lifecycle ----
    def __enter__(self) -> "RuntimeTelemetry":
        self._t0 = time.perf_counter()
        self.result["steps"] = []
        if _HAVE_PSUTIL:
            try:
                self._proc = psutil.Process()
                self._cpu_times0 = self._proc.cpu_times()
                try:
                    self._io0 = self._proc.io_counters()
                except Exception:  # noqa: BLE001 - not on macOS for some procs
                    self._io0 = None
                try:
                    self._net0 = psutil.net_io_counters()
                except Exception:  # noqa: BLE001
                    self._net0 = None
            except Exception:  # noqa: BLE001
                self._proc = None
        if self.trace_python_heap:
            try:
                if not tracemalloc.is_tracing():
                    tracemalloc.start()
                    self._started_tracemalloc = True
                tracemalloc.clear_traces()
            except Exception:  # noqa: BLE001
                self.trace_python_heap = False
        return self

    def add_step(self, label: str) -> None:
        """Record a per-step timing marker (elapsed since enter)."""
        try:
            self.result["steps"].append(
                {"label": label, "elapsed_s": _round(time.perf_counter() - self._t0)}
            )
        except Exception:  # noqa: BLE001
            pass

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            self.result["wall_clock_s"] = _round(time.perf_counter() - self._t0)
            self.result["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%S")

            # ---- CPU ----
            cpu: dict[str, Any] = {}
            if self._proc is not None:
                try:
                    ct = self._proc.cpu_times()
                    if self._cpu_times0 is not None:
                        cpu["user_s"] = _round(ct.user - self._cpu_times0.user)
                        cpu["system_s"] = _round(ct.system - self._cpu_times0.system)
                    cpu["percent"] = _round(self._proc.cpu_percent(interval=None))
                except Exception:  # noqa: BLE001
                    pass
            if _HAVE_RESOURCE:
                try:
                    ru = resource.getrusage(resource.RUSAGE_SELF)
                    cpu.setdefault("user_s", _round(ru.ru_utime))
                    cpu.setdefault("system_s", _round(ru.ru_stime))
                except Exception:  # noqa: BLE001
                    pass
            self.result["cpu"] = cpu or None

            # ---- Memory ----
            mem: dict[str, Any] = {}
            if self._proc is not None:
                try:
                    mi = self._proc.memory_info()
                    mem["rss_mib"] = _round(mi.rss / (1024 ** 2), 2)
                except Exception:  # noqa: BLE001
                    pass
            if _HAVE_RESOURCE:
                try:
                    ru = resource.getrusage(resource.RUSAGE_SELF)
                    # ru_maxrss: bytes on macOS, KiB on Linux — normalize to MiB.
                    import sys as _sys
                    factor = (1024 ** 2) if _sys.platform == "darwin" else 1024
                    mem["peak_rss_mib"] = _round(ru.ru_maxrss / factor, 2)
                except Exception:  # noqa: BLE001
                    pass
            if self.trace_python_heap:
                try:
                    cur, peak = tracemalloc.get_traced_memory()
                    mem["python_heap_current_mib"] = _round(cur / (1024 ** 2), 2)
                    mem["python_heap_peak_mib"] = _round(peak / (1024 ** 2), 2)
                    if self._started_tracemalloc:
                        tracemalloc.stop()
                except Exception:  # noqa: BLE001
                    pass
            mem["high_water_mark_mib"] = mem.get("peak_rss_mib") or mem.get("rss_mib")
            self.result["memory"] = mem or None

            # ---- Disk IO ----
            if self._proc is not None and self._io0 is not None:
                try:
                    io1 = self._proc.io_counters()
                    self.result["disk"] = {
                        "read_mib": _round((io1.read_bytes - self._io0.read_bytes) / (1024 ** 2), 3),
                        "write_mib": _round((io1.write_bytes - self._io0.write_bytes) / (1024 ** 2), 3),
                    }
                except Exception:  # noqa: BLE001
                    self.result["disk"] = None
            else:
                self.result["disk"] = None

            # ---- Network ----
            if self._net0 is not None:
                try:
                    n1 = psutil.net_io_counters()
                    self.result["network"] = {
                        "bytes_sent_mib": _round((n1.bytes_sent - self._net0.bytes_sent) / (1024 ** 2), 3),
                        "bytes_recv_mib": _round((n1.bytes_recv - self._net0.bytes_recv) / (1024 ** 2), 3),
                    }
                except Exception:  # noqa: BLE001
                    self.result["network"] = None
            else:
                self.result["network"] = None

            if exc_type is not None:
                self.result["error"] = f"{exc_type.__name__}"
        except Exception:  # noqa: BLE001 - telemetry must never mask the real work
            pass
        return False  # never suppress exceptions


def capture(name: str = "benchmark", *, trace_python_heap: bool = False) -> RuntimeTelemetry:
    """Convenience factory mirroring the context-manager constructor."""
    return RuntimeTelemetry(name, trace_python_heap=trace_python_heap)
