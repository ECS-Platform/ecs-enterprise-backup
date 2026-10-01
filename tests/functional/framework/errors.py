"""Framework exceptions."""

from __future__ import annotations


class FrameworkError(Exception):
    """Base class for framework (not ECS) problems."""


class CapabilityBlocked(FrameworkError):
    """The ECS implementation does not (yet) expose what this step needs, or a feature flag/config value is off.

    The pytest layer converts this into ``pytest.skip(<reason>)`` so the gap is visible in reports and is
    never reported as a pass. Never raise this to hide a real ECS defect.
    """

    def __init__(self, reason: str, *, requires: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.requires = requires


class WaitTimeout(FrameworkError):
    """A polling wait did not reach its target/terminal state in time."""

    def __init__(self, what: str, timeout: float, last: object = None, history: list | None = None) -> None:
        super().__init__(f"Timed out after {timeout:.0f}s waiting for {what}; last observed: {last!r}")
        self.what, self.timeout, self.last, self.history = what, timeout, last, history or []


class TerminalStateError(FrameworkError):
    """A polled job reached a terminal *failure* state while a success state was expected."""
