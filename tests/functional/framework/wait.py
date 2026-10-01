"""Wait / polling utilities for ECS asynchronous workflows.

All waits support timeout, polling interval, terminal states and meaningful errors (:class:`WaitTimeout`
carries the last observed value and the observation history).
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterable

from .errors import TerminalStateError, WaitTimeout

DEFAULT_SUCCESS = ("completed", "complete", "success", "succeeded", "done", "ok", "finished", "ingested", "indexed")
DEFAULT_FAILURE = ("failed", "failure", "error", "cancelled", "canceled", "aborted", "dead_letter")


def wait_until(predicate: Callable[[], Any], *, timeout: float = 30.0, interval: float = 1.0,
               what: str = "condition", ignore_exceptions: tuple[type[BaseException], ...] = ()) -> Any:
    """Poll ``predicate`` until it returns a truthy value (returned). Raises WaitTimeout otherwise."""
    deadline = time.monotonic() + timeout
    last: Any = None
    history: list[Any] = []
    while True:
        try:
            last = predicate()
            if last:
                return last
        except ignore_exceptions as exc:  # type: ignore[misc]
            last = f"{type(exc).__name__}: {exc}"
        history.append(last)
        if time.monotonic() >= deadline:
            raise WaitTimeout(what, timeout, last, history[-10:])
        time.sleep(interval)


def poll_job_status(fetch_status: Callable[[], Any], *, success: Iterable[str] = DEFAULT_SUCCESS,
                    failure: Iterable[str] = DEFAULT_FAILURE, timeout: float = 120.0, interval: float = 2.0,
                    what: str = "job", status_of: Callable[[Any], str] | None = None) -> Any:
    """Poll a job until a terminal state. Returns the final payload on success; raises TerminalStateError on a
    failure state and WaitTimeout when no terminal state is reached.

    ``fetch_status`` returns the payload (dict) or a status string; ``status_of`` extracts the status string
    (default: ``payload['status'|'state'|'run_status']``).
    """
    ok, bad = {s.lower() for s in success}, {s.lower() for s in failure}

    def extract(p: Any) -> str:
        if status_of:
            return str(status_of(p) or "").lower()
        if isinstance(p, dict):
            for k in ("status", "state", "run_status"):
                if p.get(k):
                    return str(p[k]).lower()
            if p.get("complete") is True or p.get("completed") is True:
                return "completed"
        return str(p or "").lower()

    seen: list[str] = []

    def probe() -> Any:
        payload = fetch_status()
        status = extract(payload)
        seen.append(status)
        if status in bad:
            raise TerminalStateError(f"{what} reached terminal failure state '{status}': {str(payload)[:300]}")
        return payload if status in ok else None

    try:
        return wait_until(probe, timeout=timeout, interval=interval, what=f"{what} to reach one of {sorted(ok)}")
    except WaitTimeout as exc:
        exc.history = seen[-10:]
        raise


def wait_for_scheduler_execution(scheduler, run_id: str, *, timeout: float = 180.0, interval: float = 2.0) -> dict:
    """Wait for an ECS scheduler collection run (GET /mvp/scheduler/run-status?run_id=...) to finish."""
    return poll_job_status(lambda: scheduler.run_status(run_id), timeout=timeout, interval=interval,
                           what=f"scheduler run {run_id}")


def wait_for_evidence(evidence, *, timeout: float = 60.0, interval: float = 2.0, **criteria: Any) -> dict:
    """Wait until evidence matching ``criteria`` (see EvidenceHelper.find) is visible in the repository."""
    return wait_until(lambda: evidence.find(**criteria), timeout=timeout, interval=interval,
                      what=f"evidence matching {criteria}")


def wait_for_ingestion(evidence, *, timeout: float = 120.0, interval: float = 3.0, min_count: int = 1, **criteria: Any) -> list:
    """Wait for >= ``min_count`` evidence rows matching ``criteria`` (connector/application/source) to be persisted."""
    return wait_until(lambda: (lambda rows: rows if len(rows) >= min_count else None)(evidence.find_all(**criteria)),
                      timeout=timeout, interval=interval, what=f"ingestion of >= {min_count} evidence item(s) {criteria}")


def wait_for_processing(fetch_state: Callable[[], Any], *, done: Callable[[Any], bool], timeout: float = 60.0,
                        interval: float = 2.0, what: str = "processing") -> Any:
    """Generic post-ingestion processing wait (validation, hashing, indexing, scoring)."""
    return wait_until(lambda: (lambda s: s if done(s) else None)(fetch_state()), timeout=timeout, interval=interval, what=what)


def wait_for_notification(notifier, *, contains: str, timeout: float = 30.0, interval: float = 2.0, **kw: Any) -> Any:
    """Wait for a notification (ECS in-app notification / notice) containing ``contains``."""
    return wait_until(lambda: notifier.find(contains=contains, **kw), timeout=timeout, interval=interval,
                      what=f"notification containing {contains!r}")
