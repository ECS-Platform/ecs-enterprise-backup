"""SharePoint via Microsoft Graph — evidence document connector.

Fetches SharePoint sites, document libraries (drives), and drive items (evidence
documents) via Microsoft Graph and normalizes them to ECS evidence-metadata
shapes. Config-driven; OAuth2 client-credentials (shared Graph base); injectable
transport (no real calls in tests); secrets never logged.

Backward compatibility: the original public surface — ``SharePointGraphClient``,
``fetch_documents``, ``normalize_document``, ``get_config``, ``is_configured``,
``masked_config``, ``health_check``, ``authenticate`` — is preserved. New,
deeper methods (sites/drives/items/folders/files) are additive.

Only METADATA is fetched — file contents are never downloaded by default
(``download_file_metadata_only`` explicitly returns metadata only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from modules.operations.integrations import _base
from modules.operations.integrations import ms_graph_base
from modules.operations.integrations._base import Transport, mask_secret
from modules.operations.integrations.ms_graph_base import (
    GRAPH_BASE,
    GRAPH_SCOPE,
    GraphAdapter,
    identity_name,
)

SOURCE = "sharepoint_graph"
#: Preserved for backward compatibility (older imports referenced this here).
TOKEN_URL_TEMPLATE = ms_graph_base.TOKEN_URL_TEMPLATE


def get_config() -> dict[str, Any]:
    """SharePoint + shared Graph config (env / YAML). Secrets read, never logged."""
    base = ms_graph_base.get_graph_config()
    cfg = _base.yaml_block(("sharepoint_graph", "sharepoint", "graph"))
    base.update({
        "site_id": (str(cfg.get("site_id")) if cfg.get("site_id") else "")
        or _base.env("ECS_GRAPH_SITE_ID"),
        "drive_id": (str(cfg.get("drive_id")) if cfg.get("drive_id") else "")
        or _base.env("ECS_GRAPH_DRIVE_ID"),
        "site_hostname": (str(cfg.get("site_hostname")) if cfg.get("site_hostname") else "")
        or _base.env("ECS_SHAREPOINT_SITE_HOSTNAME"),
        "site_path": (str(cfg.get("site_path")) if cfg.get("site_path") else "")
        or _base.env("ECS_SHAREPOINT_SITE_PATH"),
        "folder_path": (str(cfg.get("folder_path")) if cfg.get("folder_path") else "")
        or _base.env("ECS_SHAREPOINT_FOLDER_PATH"),
    })
    return base


def is_configured() -> bool:
    c = get_config()
    return bool(c["tenant_id"] and c["client_id"] and c["client_secret"] and c["site_id"])


def masked_config(cfg: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    cfg = cfg or get_config()
    return {
        "integration": "SharePoint / Microsoft Graph",
        "base_url_configured": bool(cfg.get("base_url")),
        "tenant_id": mask_secret(cfg.get("tenant_id")),
        "client_id": mask_secret(cfg.get("client_id")),
        "client_secret": mask_secret(cfg.get("client_secret")),
        "site_id": mask_secret(cfg.get("site_id")),
        "drive_id": mask_secret(cfg.get("drive_id")),
        "access_token": mask_secret(cfg.get("access_token")),
        "site_hostname": cfg.get("site_hostname") or "",
        "site_path": cfg.get("site_path") or "",
        "folder_path": cfg.get("folder_path") or "",
        "scope": cfg.get("scope"),
        "timeout_sec": cfg.get("timeout_sec"),
        "max_retries": cfg.get("max_retries"),
        "ready": bool(cfg.get("tenant_id") and cfg.get("client_id")
                      and cfg.get("client_secret") and cfg.get("site_id")),
    }


@dataclass(repr=False)  # inherit BaseAdapter's secret-safe __repr__
class SharePointGraphClient(GraphAdapter):
    source: str = SOURCE
    config: dict[str, Any] = field(default_factory=get_config)
    transport: Optional[Transport] = None

    def is_configured(self) -> bool:
        c = self.config
        return bool(c.get("tenant_id") and c.get("client_id")
                    and c.get("client_secret") and c.get("site_id"))

    def masked_config(self) -> dict[str, Any]:
        return masked_config(self.config)

    def _health_path(self) -> str:
        return f"sites/{self.config.get('site_id', '')}"

    def health_check(self) -> dict[str, Any]:  # keep config-based health (no live probe by default)
        if not self.is_configured():
            return {**_base.not_configured_response(SOURCE), "configured": False,
                    "masked_config": self.masked_config()}
        return {"ok": True, "source": SOURCE, "status": "ok", "configured": True,
                "items": [], "errors": [], "masked_config": self.masked_config()}

    # ---- sites ------------------------------------------------------------ #
    def fetch_sites(self, search: str = "", max_items: int = 200) -> dict[str, Any]:
        """List/search SharePoint sites the app can see."""
        params = {"search": search} if search else {"$top": min(max_items, 200)}
        return self.graph_collect("sites", normalize_site, params=params,
                                  max_items=max_items)

    def resolve_site_by_path(self, hostname: str = "", site_path: str = "") -> dict[str, Any]:
        """Resolve a site by ``{hostname}:/{site_path}`` -> normalized site."""
        hostname = hostname or self.config.get("site_hostname") or ""
        site_path = site_path or self.config.get("site_path") or ""
        if not hostname or not site_path:
            return _base.error_response(SOURCE, "http_error",
                                        "site_hostname and site_path are required")
        path = f"sites/{hostname}:/{site_path.strip('/')}"
        return self.graph_get_one(path, normalize_site)

    # ---- drives (document libraries) -------------------------------------- #
    def fetch_drives(self, site_id: str = "", max_items: int = 200) -> dict[str, Any]:
        """List document libraries (drives) for a site."""
        site_id = site_id or self.config.get("site_id") or ""
        return self.graph_collect(f"sites/{site_id}/drives", normalize_drive,
                                  max_items=max_items)

    # ---- drive items ------------------------------------------------------ #
    def fetch_drive_items(self, drive_id: str = "", max_items: int = 1000) -> dict[str, Any]:
        """List items at the root of a drive (or the site's default drive)."""
        drive_id = drive_id or self.config.get("drive_id") or ""
        site_id = self.config.get("site_id") or ""
        path = (f"drives/{drive_id}/root/children" if drive_id
                else f"sites/{site_id}/drive/root/children")
        return self.graph_collect(path, normalize_item, max_items=max_items)

    def fetch_folder_items(self, folder_path: str = "", drive_id: str = "",
                           max_items: int = 1000) -> dict[str, Any]:
        """List items within a folder path of a drive."""
        drive_id = drive_id or self.config.get("drive_id") or ""
        folder_path = folder_path or self.config.get("folder_path") or ""
        if not drive_id:
            return _base.error_response(SOURCE, "http_error", "drive_id is required")
        if not folder_path:
            return self.fetch_drive_items(drive_id=drive_id, max_items=max_items)
        path = f"drives/{drive_id}/root:/{folder_path.strip('/')}:/children"
        return self.graph_collect(path, normalize_item, max_items=max_items)

    def fetch_file_metadata(self, item_id: str, drive_id: str = "") -> dict[str, Any]:
        """Fetch a single drive item's metadata by id (no content)."""
        drive_id = drive_id or self.config.get("drive_id") or ""
        if not drive_id or not item_id:
            return _base.error_response(SOURCE, "http_error",
                                        "drive_id and item_id are required")
        return self.graph_get_one(f"drives/{drive_id}/items/{item_id}", normalize_item)

    def download_file_metadata_only(self, item_id: str, drive_id: str = "") -> dict[str, Any]:
        """Explicit metadata-only accessor (contents are NEVER downloaded)."""
        return self.fetch_file_metadata(item_id, drive_id=drive_id)

    # ---- backward-compatible documents API -------------------------------- #
    def fetch_documents(self, page_size: int = _base.DEFAULT_PAGE_SIZE,
                        max_items: int = 1000) -> dict[str, Any]:
        """Backward-compatible: list evidence documents from the configured drive.

        Uses nextLink pagination under the hood; ``page_size`` is accepted for
        API compatibility and passed as ``$top``.
        """
        if not self.is_configured():
            return _base.not_configured_response(SOURCE)
        drive = self.config.get("drive_id") or ""
        site = self.config.get("site_id") or ""
        path = (f"drives/{drive}/root/children" if drive
                else f"sites/{site}/drive/root/children")
        return self.graph_collect(
            path, normalize_document,
            params={"$top": _base.clamp_page_size(page_size)},
            max_items=max_items,
        )


# --------------------------------------------------------------------------- #
# Normalizers
# --------------------------------------------------------------------------- #
def normalize_site(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "site_id": record.get("id", ""),
        "name": record.get("displayName", record.get("name", "")),
        "web_url": record.get("webUrl", ""),
        "created_datetime": record.get("createdDateTime", ""),
        "last_modified": record.get("lastModifiedDateTime", ""),
        "source": SOURCE,
        "evidence_type": "sharepoint_site",
    }


def normalize_drive(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "drive_id": record.get("id", ""),
        "name": record.get("name", ""),
        "drive_type": record.get("driveType", ""),
        "web_url": record.get("webUrl", ""),
        "created_datetime": record.get("createdDateTime", ""),
        "source": SOURCE,
        "evidence_type": "sharepoint_drive",
    }


def normalize_item(record: dict[str, Any]) -> dict[str, Any]:
    """Rich evidence-metadata normalization for a SharePoint/Graph drive item."""
    file_info = record.get("file", {}) if isinstance(record.get("file"), dict) else {}
    return {
        "source": SOURCE,
        "item_id": record.get("id", ""),
        "name": record.get("name", ""),
        "web_url": record.get("webUrl", ""),
        "size": record.get("size", 0),
        "created_datetime": record.get("createdDateTime", ""),
        "modified_datetime": record.get("lastModifiedDateTime", ""),
        "created_by": identity_name(record.get("createdBy")),
        "modified_by": identity_name(record.get("lastModifiedBy")),
        "mime_type": (file_info.get("mimeType", "") if file_info else ""),
        "parent_reference": record.get("parentReference", {}) or {},
        "is_folder": "folder" in record,
        "evidence_type": "sharepoint_document",
    }


def normalize_document(record: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible document shape (original keys preserved)."""
    return {
        "item_id": record.get("id", ""),
        "name": record.get("name", ""),
        "size_bytes": record.get("size", 0),
        "last_modified": record.get("lastModifiedDateTime", ""),
        "web_url": record.get("webUrl", ""),
        "is_folder": "folder" in record,
        "source": SOURCE,
    }


def health_check() -> dict[str, Any]:
    return SharePointGraphClient().health_check()
