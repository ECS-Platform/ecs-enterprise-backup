"""Outlook Email via Microsoft Graph — mail evidence connector.

Fetches mail folders, messages, a single message, and attachment METADATA for a
target mailbox via Microsoft Graph, normalizing to ECS evidence-metadata shapes.
Config-driven; OAuth2 client-credentials (shared Graph base); injectable transport
(no real calls in tests); secrets never logged.

Attachment CONTENTS are never downloaded — only attachment metadata is captured.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations import ms_graph_base
from modules.operations.integrations._base import Transport, mask_secret

SOURCE = "outlook_graph"
DEFAULT_MESSAGE_LIMIT = 50
DEFAULT_MAIL_FOLDER = "inbox"


def get_config() -> dict[str, Any]:
    """Outlook + shared Graph config (env / YAML). Secrets read, never logged."""
    base = ms_graph_base.get_graph_config()
    cfg = _base.yaml_block(("outlook_graph", "outlook"))
    base.update({
        "user_id": (str(cfg.get("user_id")) if cfg.get("user_id") else "")
        or _base.env("ECS_OUTLOOK_USER_ID"),
        "mail_folder": (str(cfg.get("mail_folder")) if cfg.get("mail_folder") else "")
        or _base.env("ECS_OUTLOOK_MAIL_FOLDER") or DEFAULT_MAIL_FOLDER,
        "message_limit": _base.safe_int(
            cfg.get("message_limit") or _base.env("ECS_OUTLOOK_MESSAGE_LIMIT"),
            DEFAULT_MESSAGE_LIMIT,
        ),
    })
    return base


def is_configured() -> bool:
    c = get_config()
    # A target mailbox (user_id) is required in addition to the shared Graph creds.
    return bool(ms_graph_base.is_graph_configured(c) and c.get("user_id"))


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "Outlook (Graph)",
        **ms_graph_base.graph_masked_config(cfg),
        "user_id": mask_secret(cfg.get("user_id")),
        "mail_folder": cfg.get("mail_folder") or "",
        "message_limit": cfg.get("message_limit"),
        "ready": bool(ms_graph_base.is_graph_configured(cfg) and cfg.get("user_id")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class OutlookGraphClient(ms_graph_base.GraphAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(ms_graph_base.is_graph_configured(c) and c.get("user_id"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def health_check(self) -> dict[str, Any]:
        if not self.is_configured():
            return {**_base.not_configured_response(SOURCE), "configured": False,
                    "masked_config": self.masked_config()}
        return {"ok": True, "source": SOURCE, "status": "ok", "configured": True,
                "items": [], "errors": [], "masked_config": self.masked_config()}

    def _user(self, user_id: str = "") -> str:
        return user_id or self.config.get("user_id") or ""

    # ---- mail folders ----------------------------------------------------- #
    def fetch_mail_folders(self, user_id: str = "", max_items: int = 200) -> dict[str, Any]:
        user = self._user(user_id)
        if not user:
            return _base.error_response(SOURCE, "http_error", "user_id is required")
        return self.graph_collect(f"users/{user}/mailFolders", normalize_folder,
                                  max_items=max_items)

    # ---- messages --------------------------------------------------------- #
    def fetch_messages(self, user_id: str = "", folder: str = "",
                       limit: int = 0) -> dict[str, Any]:
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        user = self._user(user_id)
        if not user:
            return _base.error_response(SOURCE, "http_error", "user_id is required")
        folder = folder or self.config.get("mail_folder") or DEFAULT_MAIL_FOLDER
        limit = limit or self.config.get("message_limit") or DEFAULT_MESSAGE_LIMIT
        return self.graph_collect(
            f"users/{user}/mailFolders/{folder}/messages",
            normalize_message,
            params={"$top": _base.clamp_page_size(limit, DEFAULT_MESSAGE_LIMIT)},
            max_items=limit,
        )

    def fetch_message(self, user_id: str = "", message_id: str = "") -> dict[str, Any]:
        user = self._user(user_id)
        if not user or not message_id:
            return _base.error_response(SOURCE, "http_error",
                                        "user_id and message_id are required")
        return self.graph_get_one(f"users/{user}/messages/{message_id}", normalize_message)

    def fetch_attachments_metadata(self, user_id: str = "",
                                   message_id: str = "") -> dict[str, Any]:
        """Fetch attachment METADATA only (contents are never downloaded)."""
        user = self._user(user_id)
        if not user or not message_id:
            return _base.error_response(SOURCE, "http_error",
                                        "user_id and message_id are required")
        # $select excludes contentBytes so no attachment content is retrieved.
        return self.graph_collect(
            f"users/{user}/messages/{message_id}/attachments",
            normalize_attachment_metadata,
            params={"$select": "id,name,contentType,size,isInline,lastModifiedDateTime"},
        )


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def normalize_folder(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "folder_id": record.get("id", ""),
        "name": record.get("displayName", ""),
        "total_item_count": record.get("totalItemCount", 0),
        "unread_item_count": record.get("unreadItemCount", 0),
        "evidence_type": "outlook_folder",
    }


def _addresses(nodes: Any) -> list[str]:
    out: list[str] = []
    if isinstance(nodes, list):
        for n in nodes:
            addr = (n or {}).get("emailAddress", {}) if isinstance(n, dict) else {}
            val = addr.get("address") or addr.get("name")
            if val:
                out.append(str(val))
    return out


def normalize_message(record: dict[str, Any]) -> dict[str, Any]:
    sender = record.get("sender", record.get("from", {})) or {}
    sender_addr = (sender.get("emailAddress", {}) or {}) if isinstance(sender, dict) else {}
    return {
        "source": SOURCE,
        "message_id": record.get("id", ""),
        "subject": record.get("subject", "") or "",
        "sender": sender_addr.get("address", sender_addr.get("name", "")),
        "recipients": _addresses(record.get("toRecipients")),
        "received_datetime": record.get("receivedDateTime", ""),
        "has_attachments": bool(record.get("hasAttachments", False)),
        "importance": record.get("importance", ""),
        "body_preview": str(record.get("bodyPreview", "") or "")[:280],
        "web_link": record.get("webLink", ""),
        "evidence_type": "outlook_message",
    }


def normalize_attachment_metadata(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": SOURCE,
        "attachment_id": record.get("id", ""),
        "name": record.get("name", ""),
        "content_type": record.get("contentType", ""),
        "size": record.get("size", 0),
        "is_inline": bool(record.get("isInline", False)),
        "last_modified": record.get("lastModifiedDateTime", ""),
        "evidence_type": "outlook_attachment",
    }


def health_check() -> dict[str, Any]:
    return OutlookGraphClient().health_check()
