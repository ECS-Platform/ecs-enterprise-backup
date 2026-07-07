"""Microsoft Teams via Microsoft Graph — collaboration evidence connector.

Fetches Teams, channels, channel messages, and channel tabs via Microsoft Graph
and normalizes them to ECS evidence-metadata shapes. Config-driven; OAuth2
client-credentials (shared Graph base); injectable transport (no real calls in
tests); secrets never logged.

Only metadata/message previews are captured (never full attachment contents).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations import ms_graph_base
from modules.operations.integrations._base import Transport, mask_secret
from modules.operations.integrations.ms_graph_base import GraphAdapter, identity_name

SOURCE = "teams_graph"
DEFAULT_MESSAGE_LIMIT = 50


def get_config() -> dict[str, Any]:
    """Teams + shared Graph config (env / YAML). Secrets read, never logged."""
    base = ms_graph_base.get_graph_config()
    cfg = _base.yaml_block(("teams_graph", "teams"))
    base.update({
        "team_id": (str(cfg.get("team_id")) if cfg.get("team_id") else "")
        or _base.env("ECS_TEAMS_TEAM_ID"),
        "channel_id": (str(cfg.get("channel_id")) if cfg.get("channel_id") else "")
        or _base.env("ECS_TEAMS_CHANNEL_ID"),
        "message_limit": _base.safe_int(
            cfg.get("message_limit") or _base.env("ECS_TEAMS_MESSAGE_LIMIT"),
            DEFAULT_MESSAGE_LIMIT,
        ),
    })
    return base


def is_configured() -> bool:
    return ms_graph_base.is_graph_configured(get_config())


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Microsoft Teams (Graph)",
        **ms_graph_base.graph_masked_config(cfg),
        "team_id": mask_secret(cfg.get("team_id")),
        "channel_id": mask_secret(cfg.get("channel_id")),
        "message_limit": cfg.get("message_limit"),
        "ready": ms_graph_base.is_graph_configured(cfg),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class TeamsGraphClient(GraphAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def _health_path(self) -> str:
        return "teams"

    def health_check(self) -> dict[str, Any]:
        if not self.is_configured():
            return {**_base.not_configured_response(SOURCE), "configured": False,
                    "masked_config": self.masked_config()}
        return {"ok": True, "source": SOURCE, "status": "ok", "configured": True,
                "items": [], "errors": [], "masked_config": self.masked_config()}

    # ---- teams / channels ------------------------------------------------- #
    def fetch_teams(self, max_items: int = 200) -> dict[str, Any]:
        """List joined teams the app identity can see."""
        return self.graph_collect("teams", normalize_team, max_items=max_items)

    def fetch_team(self, team_id: str = "") -> dict[str, Any]:
        team_id = team_id or self.config.get("team_id") or ""
        if not team_id:
            return _base.error_response(SOURCE, "http_error", "team_id is required")
        return self.graph_get_one(f"teams/{team_id}", normalize_team)

    def fetch_channels(self, team_id: str = "", max_items: int = 200) -> dict[str, Any]:
        team_id = team_id or self.config.get("team_id") or ""
        if not team_id:
            return _base.error_response(SOURCE, "http_error", "team_id is required")
        return self.graph_collect(f"teams/{team_id}/channels", normalize_channel,
                                  max_items=max_items)

    def fetch_channel_messages(self, team_id: str = "", channel_id: str = "",
                               limit: int = 0) -> dict[str, Any]:
        team_id = team_id or self.config.get("team_id") or ""
        channel_id = channel_id or self.config.get("channel_id") or ""
        if not team_id or not channel_id:
            return _base.error_response(SOURCE, "http_error",
                                        "team_id and channel_id are required")
        limit = limit or self.config.get("message_limit") or DEFAULT_MESSAGE_LIMIT
        return self.graph_collect(
            f"teams/{team_id}/channels/{channel_id}/messages",
            normalize_message,
            params={"$top": _base.clamp_page_size(limit, DEFAULT_MESSAGE_LIMIT)},
            max_items=limit,
        )

    def fetch_channel_tabs(self, team_id: str = "", channel_id: str = "") -> dict[str, Any]:
        team_id = team_id or self.config.get("team_id") or ""
        channel_id = channel_id or self.config.get("channel_id") or ""
        if not team_id or not channel_id:
            return _base.error_response(SOURCE, "http_error",
                                        "team_id and channel_id are required")
        return self.graph_collect(
            f"teams/{team_id}/channels/{channel_id}/tabs", normalize_tab)


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def normalize_team(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "team_id": record.get("id", ""),
        "name": record.get("displayName", ""),
        "description": record.get("description", ""),
        "web_url": record.get("webUrl", ""),
        "visibility": record.get("visibility", ""),
        "evidence_type": "teams_team",
    }


def normalize_channel(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "channel_id": record.get("id", ""),
        "name": record.get("displayName", ""),
        "description": record.get("description", ""),
        "web_url": record.get("webUrl", ""),
        "membership_type": record.get("membershipType", ""),
        "created_datetime": record.get("createdDateTime", ""),
        "evidence_type": "teams_channel",
    }


def normalize_message(record: dict[str, Any]) -> dict[str, Any]:
    body = record.get("body", {}) if isinstance(record.get("body"), dict) else {}
    return {
        "source": SOURCE,
        "message_id": record.get("id", ""),
        "subject": record.get("subject", "") or "",
        "body_preview": _preview(body.get("content", "")),
        "from_user": identity_name(record.get("from")),
        "created_datetime": record.get("createdDateTime", ""),
        "importance": record.get("importance", ""),
        "web_url": record.get("webUrl", ""),
        "evidence_type": "teams_message",
    }


def normalize_tab(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "tab_id": record.get("id", ""),
        "name": record.get("displayName", ""),
        "web_url": record.get("webUrl", ""),
        "evidence_type": "teams_tab",
    }


def _preview(html_or_text: Any, limit: int = 280) -> str:
    """Truncated, non-secret preview of a message body (tags stripped naively)."""
    text = str(html_or_text or "")
    # Very light tag strip for previews; not a full HTML parser (metadata only).
    if "<" in text and ">" in text:
        import re
        text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())
    return text[:limit]


def health_check() -> dict[str, Any]:
    return TeamsGraphClient().health_check()
