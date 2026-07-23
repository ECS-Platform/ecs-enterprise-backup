"""Framework Control Master repository — Phase-1 file catalogue with swappable backend.

The dashboard and API must depend on :class:`FrameworkControlRepository` only.
Phase-1 uses YAML under ``config/framework_control_master/``. Future backends
(database, Excel import, SharePoint, framework upload) implement the same
interface without changing consumers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_DIR = _REPO_ROOT / "config" / "framework_control_master"
_CATALOG_PATH = _CATALOG_DIR / "catalog.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml

        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


class FrameworkControlRepository(ABC):
    """Abstract storage for framework control master data."""

    @abstractmethod
    def source_type(self) -> str:
        """Backend identifier, e.g. ``file``, ``database``, ``excel``."""

    @abstractmethod
    def list_framework_summaries(self) -> list[dict[str, Any]]:
        """Lightweight framework index rows for catalogue browser."""

    @abstractmethod
    def get_framework(self, framework_id: str) -> dict[str, Any] | None:
        """Full framework document including policies, controls, procedures, evidence."""

    @abstractmethod
    def get_control(self, framework_id: str, control_id: str) -> dict[str, Any] | None:
        """Single control with nested procedures and evidence requirements."""

    @abstractmethod
    def search_controls(
        self,
        query: str = "",
        framework_id: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        """Cross-framework control search."""

    @abstractmethod
    def catalog_stats(self) -> dict[str, Any]:
        """Aggregate counts for dashboard KPI strip."""

    @abstractmethod
    def list_application_assignments(self) -> list[dict[str, Any]]:
        """Application ↔ framework assignment rows."""

    @abstractmethod
    def frameworks_for_application(self, application: str) -> list[str]:
        """Framework IDs assigned to an application."""

    @abstractmethod
    def applications_for_framework(self, framework_id: str) -> list[str]:
        """Applications assigned to a framework."""

    @abstractmethod
    def is_control_applicable(
        self, application: str, framework_id: str, control_id: str
    ) -> bool:
        """False when explicitly marked not applicable for the application."""

    @abstractmethod
    def resolve_framework_id(self, framework_id: str) -> str:
        """Resolve aliases to canonical framework id."""


class FileFrameworkControlRepository(FrameworkControlRepository):
    """Phase-1 repository backed by ``config/framework_control_master/`` YAML."""

    def __init__(self, catalog_dir: Path | None = None) -> None:
        self._catalog_dir = catalog_dir or _CATALOG_DIR
        self._catalog_path = self._catalog_dir / "catalog.yaml"
        self._assignments_path = self._catalog_dir / "application_assignments.yaml"

    def source_type(self) -> str:
        return "file"

    @lru_cache(maxsize=1)
    def _catalog(self) -> dict[str, Any]:
        return _load_yaml(self._catalog_path)

    @lru_cache(maxsize=1)
    def _assignments_doc(self) -> dict[str, Any]:
        return _load_yaml(self._assignments_path)

    def _resolve_id(self, framework_id: str) -> str:
        key = (framework_id or "").strip()
        if not key:
            return key
        aliases = self._catalog().get("aliases") or {}
        resolved = aliases.get(key) or aliases.get(key.upper()) or key
        for entry in self._catalog().get("frameworks") or []:
            if entry.get("id") == resolved:
                return resolved
            if entry.get("code") == key or entry.get("name") == key:
                return entry["id"]
        return resolved

    def resolve_framework_id(self, framework_id: str) -> str:
        return self._resolve_id(framework_id)

    def _framework_path(self, framework_id: str) -> Path | None:
        resolved = self._resolve_id(framework_id)
        for entry in self._catalog().get("frameworks") or []:
            if entry.get("id") == resolved:
                rel = entry.get("file") or f"frameworks/{resolved}.yaml"
                return self._catalog_dir / rel
        fallback = self._catalog_dir / "frameworks" / f"{resolved}.yaml"
        return fallback if fallback.is_file() else None

    @lru_cache(maxsize=32)
    def _load_framework_doc(self, framework_id: str) -> dict[str, Any]:
        path = self._framework_path(framework_id)
        if not path:
            return {}
        doc = _load_yaml(path)
        fw = doc.get("framework") or {}
        fw.setdefault("id", self._resolve_id(framework_id))
        doc["framework"] = fw
        return doc

    def list_framework_summaries(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self._catalog().get("frameworks") or []:
            fw_id = entry.get("id", "")
            doc = self._load_framework_doc(fw_id)
            fw = doc.get("framework") or {}
            controls = doc.get("controls") or []
            policies = doc.get("policies") or []
            rows.append(
                {
                    "id": fw_id,
                    "code": fw.get("code") or entry.get("code", ""),
                    "name": fw.get("name") or entry.get("name", ""),
                    "display_name": fw.get("display_name") or entry.get("display_name", ""),
                    "category": fw.get("category") or entry.get("category", ""),
                    "regulator": fw.get("regulator", ""),
                    "version": fw.get("version", ""),
                    "description": fw.get("description", ""),
                    "control_count": len(controls) or entry.get("control_count", 0),
                    "policy_count": len(policies) or entry.get("policy_count", 0),
                    "procedure_count": sum(len(c.get("procedures") or []) for c in controls),
                    "evidence_requirement_count": sum(
                        len(c.get("evidence_requirements") or []) for c in controls
                    ),
                    "source_type": self.source_type(),
                }
            )
        return rows

    def get_framework(self, framework_id: str) -> dict[str, Any] | None:
        doc = self._load_framework_doc(framework_id)
        if not doc.get("framework"):
            return None
        fw = doc["framework"]
        controls = doc.get("controls") or []
        policies = doc.get("policies") or []
        return {
            "framework": {**fw, "source_type": self.source_type()},
            "policies": policies,
            "controls": controls,
            "stats": {
                "policy_count": len(policies),
                "control_count": len(controls),
                "procedure_count": sum(len(c.get("procedures") or []) for c in controls),
                "evidence_requirement_count": sum(
                    len(c.get("evidence_requirements") or []) for c in controls
                ),
            },
        }

    def get_control(self, framework_id: str, control_id: str) -> dict[str, Any] | None:
        doc = self.get_framework(framework_id)
        if not doc:
            return None
        cid = (control_id or "").strip()
        for control in doc.get("controls") or []:
            if control.get("id") == cid:
                policy_map = {p["id"]: p for p in doc.get("policies") or [] if p.get("id")}
                linked = [
                    policy_map[ref]
                    for ref in control.get("policy_refs") or []
                    if ref in policy_map
                ]
                return {
                    "framework": doc["framework"],
                    "control": control,
                    "linked_policies": linked,
                }
        return None

    def search_controls(
        self,
        query: str = "",
        framework_id: str | None = None,
        domain: str | None = None,
    ) -> list[dict[str, Any]]:
        q = (query or "").strip().lower()
        dom = (domain or "").strip().lower()
        summaries = self.list_framework_summaries()
        targets = summaries
        if framework_id:
            resolved = self._resolve_id(framework_id)
            targets = [s for s in summaries if s["id"] == resolved]
        hits: list[dict[str, Any]] = []
        for summary in targets:
            doc = self.get_framework(summary["id"])
            if not doc:
                continue
            for control in doc.get("controls") or []:
                if dom and (control.get("domain") or "").lower() != dom:
                    continue
                hay = " ".join(
                    str(control.get(k) or "")
                    for k in ("id", "title", "domain", "description")
                ).lower()
                if q and q not in hay:
                    continue
                hits.append(
                    {
                        "framework_id": summary["id"],
                        "framework_name": summary["display_name"],
                        "framework_code": summary["code"],
                        **control,
                    }
                )
        return hits

    def catalog_stats(self) -> dict[str, Any]:
        summaries = self.list_framework_summaries()
        return {
            "framework_count": len(summaries),
            "control_count": sum(s.get("control_count", 0) for s in summaries),
            "policy_count": sum(s.get("policy_count", 0) for s in summaries),
            "procedure_count": sum(s.get("procedure_count", 0) for s in summaries),
            "evidence_requirement_count": sum(
                s.get("evidence_requirement_count", 0) for s in summaries
            ),
            "source_type": self.source_type(),
            "catalog_version": self._catalog().get("catalog_version", ""),
        }

    def list_application_assignments(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for entry in self._assignments_doc().get("assignments") or []:
            if not isinstance(entry, dict):
                continue
            app = str(entry.get("application") or "").strip()
            if not app:
                continue
            fw_ids = [
                self._resolve_id(str(fw))
                for fw in (entry.get("frameworks") or [])
                if fw
            ]
            rows.append(
                {
                    "application": app,
                    "owner": entry.get("owner", ""),
                    "framework_ids": fw_ids,
                }
            )
        return rows

    def frameworks_for_application(self, application: str) -> list[str]:
        app = (application or "").strip()
        for entry in self.list_application_assignments():
            if entry["application"] == app:
                return list(entry["framework_ids"])
        return []

    def applications_for_framework(self, framework_id: str) -> list[str]:
        resolved = self._resolve_id(framework_id)
        apps: list[str] = []
        for entry in self.list_application_assignments():
            if resolved in entry.get("framework_ids", []):
                apps.append(entry["application"])
        return apps

    def is_control_applicable(
        self, application: str, framework_id: str, control_id: str
    ) -> bool:
        resolved = self._resolve_id(framework_id)
        cid = (control_id or "").strip()
        app = (application or "").strip()
        for entry in self._assignments_doc().get("not_applicable") or []:
            if not isinstance(entry, dict):
                continue
            if entry.get("application") == app and self._resolve_id(
                str(entry.get("framework_id") or "")
            ) == resolved:
                excluded = {str(x) for x in (entry.get("control_ids") or [])}
                if cid in excluded:
                    return False
        return bool(self.frameworks_for_application(app)) and resolved in self.frameworks_for_application(app)


def get_framework_control_repository() -> FrameworkControlRepository:
    """Factory — swap implementation via env/config in a later phase."""
    return FileFrameworkControlRepository()
