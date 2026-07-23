"""Deterministic SharePoint evidence-folder path parser.

Contract (relative to an evidence root, no fuzzy matching):

    <Application>/<Environment>/<Framework>/<Control>/<file>
    <Application>/<Environment>/<Framework>/<Control>/<nested...>/<file>

Canonical fields: application, environment, framework, control_or_observation,
relative_folder_path. Invalid or shallow paths return a structured rejection
without raising.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import unquote

# Align with ECS framework catalog environments (exact match, case-sensitive).
SUPPORTED_ENVIRONMENTS = frozenset({
    "Production",
    "PROD",
    "DR",
    "UAT",
    "SOC Production",
})

REJECTION_INCOMPLETE = "incomplete_path"
REJECTION_UNSUPPORTED_ENV = "unsupported_environment"
REJECTION_EMPTY = "empty_path"


def decode_path(path: str) -> str:
    """URL-decode and normalize slash separators (deterministic, no fuzzy logic)."""
    decoded = unquote(path or "")
    return decoded.replace("\\", "/").strip("/")


def _split_segments(path: str) -> list[str]:
    normalized = decode_path(path)
    if not normalized:
        return []
    return [seg for seg in normalized.split("/") if seg]


def parse_evidence_folder_path(
    relative_path: str,
    *,
    filename: str = "",
) -> dict[str, Any]:
    """Parse a path relative to the evidence root into canonical contract fields.

    When ``filename`` is omitted, the last segment of ``relative_path`` is treated
    as the filename (requires at least five segments). When ``filename`` is given,
    ``relative_path`` is the parent folder path relative to the evidence root and
    must contain at least four segments (application through control).
    """
    segments = _split_segments(relative_path)
    file_name = (filename or "").strip()

    if file_name:
        folder_segments = segments
        if len(folder_segments) < 4:
            return _reject(
                REJECTION_INCOMPLETE,
                f"Path has {len(folder_segments)} folder segment(s); "
                "need application/environment/framework/control",
                segments=folder_segments,
                filename=file_name,
            )
    else:
        if len(segments) < 5:
            return _reject(
                REJECTION_INCOMPLETE,
                f"Path has {len(segments)} segment(s); "
                "need application/environment/framework/control/filename",
                segments=segments,
            )
        folder_segments = segments[:-1]
        file_name = segments[-1]

    application = folder_segments[0]
    environment = folder_segments[1]
    framework = folder_segments[2]
    control_or_observation = folder_segments[3]

    if environment not in SUPPORTED_ENVIRONMENTS:
        return _reject(
            REJECTION_UNSUPPORTED_ENV,
            f"Environment '{environment}' is not supported",
            segments=folder_segments,
            filename=file_name,
            application=application,
            environment=environment,
            framework=framework,
            control_or_observation=control_or_observation,
        )

    relative_folder_path = "/".join(folder_segments)
    return {
        "ok": True,
        "application": application,
        "environment": environment,
        "framework": framework,
        "control_or_observation": control_or_observation,
        "relative_folder_path": relative_folder_path,
        "filename": file_name,
        "rejection_code": "",
        "rejection_reason": "",
    }


def _reject(
    code: str,
    reason: str,
    *,
    segments: list[str],
    filename: str = "",
    application: str = "",
    environment: str = "",
    framework: str = "",
    control_or_observation: str = "",
) -> dict[str, Any]:
    if not segments and code != REJECTION_EMPTY:
        code = REJECTION_EMPTY
        reason = "Path is empty"
    return {
        "ok": False,
        "application": application,
        "environment": environment,
        "framework": framework,
        "control_or_observation": control_or_observation,
        "relative_folder_path": "/".join(segments) if segments else "",
        "filename": filename,
        "rejection_code": code,
        "rejection_reason": reason,
    }
