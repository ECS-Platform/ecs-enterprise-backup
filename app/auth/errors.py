"""Authentication error types.

Kept separate from authorization: every error here is an *authentication*
failure (missing/invalid identity), mapped to HTTP 401. Authorization (403) is
out of scope for Phase 1.
"""

from __future__ import annotations


class AuthenticationError(Exception):
    """Raised when a request cannot be authenticated.

    `reason` is a short machine-friendly code (e.g. 'missing_token',
    'invalid_signature', 'expired', 'audience_mismatch') used for audit events;
    `detail` is a human-readable message safe to return to the client.
    """

    http_status = 401

    def __init__(self, reason: str, detail: str = "Authentication required") -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
