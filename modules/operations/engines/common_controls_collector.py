"""Deterministic Common Control evidence collection for the MVP scheduler.

Discovers ``CommonControls/<slug>/`` folders, ingests mock evidence, validates
deterministically (no LLM), persists via the existing evidence repository +
object custody path, and raises observations on validation failure.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from modules.audit_intelligence.engines import evidence_repository as ai_repo
from modules.audit_intelligence.engines import observation_generation as obs_gen
from modules.audit_intelligence.models import (
    CONTROL_STATUS_COMPLIANT,
    CONTROL_STATUS_NON_COMPLIANT,
    CONTROL_STATUS_NEEDS_REVIEW,
    VERDICT_FAIL,
    VERDICT_PASS,
    VERDICT_WARNING,
    ValidationResult,
)
from modules.operations.engines.common_controls_catalog import (
    COMMON_CONTROLS,
    CommonControlDef,
    by_slug,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
COMMON_CONTROLS_ROOT = _REPO_ROOT / "CommonControls"


@dataclass
class CollectionReceipt:
    slug: str
    common_control: str
    control_id: str
    discovered: bool = False
    collected: bool = False
    metadata_persisted: bool = False
    object_stored: bool = False
    verdict: str = ""
    observation_id: str = ""
    evidence_key: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "common_control": self.common_control,
            "control_id": self.control_id,
            "discovered": self.discovered,
            "collected": self.collected,
            "metadata_persisted": self.metadata_persisted,
            "object_stored": self.object_stored,
            "verdict": self.verdict,
            "observation_id": self.observation_id,
            "evidence_key": self.evidence_key,
            "error": self.error,
        }


@dataclass
class CollectionRun:
    run_id: str
    folders_discovered: int = 0
    collected: int = 0
    observations: int = 0
    receipts: list[CollectionReceipt] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        postgresql_count = sum(1 for r in self.receipts if r.metadata_persisted)
        object_storage_count = sum(1 for r in self.receipts if r.object_stored)
        failures = sum(1 for r in self.receipts if r.error and not r.collected)
        return {
            "run_id": self.run_id,
            "folders_discovered": self.folders_discovered,
            "files_discovered": self.folders_discovered,
            "collected": self.collected,
            "new_evidence": self.collected,
            "observations": self.observations,
            "postgresql_count": postgresql_count,
            "object_storage_count": object_storage_count,
            "pgvector_count": 0,
            "failures": failures,
            "duplicates_skipped": 0,
            "receipts": [r.to_dict() for r in self.receipts],
        }


def common_controls_root() -> Path:
    override = os.environ.get("ECS_COMMON_CONTROLS_ROOT", "").strip()
    return Path(override) if override else COMMON_CONTROLS_ROOT


def discover_common_control_folders(root: Path | None = None) -> list[Path]:
    """Return sorted CommonControls subfolders that contain a manifest.json."""
    base = root or common_controls_root()
    if not base.is_dir():
        return []
    out: list[Path] = []
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / "manifest.json").is_file():
            out.append(child)
    return out


def load_manifest(folder: Path) -> dict[str, Any]:
    raw = (folder / "manifest.json").read_text(encoding="utf-8")
    return json.loads(raw)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rule_passes(data: dict[str, Any], rule: dict[str, Any]) -> tuple[bool, str]:
    field_name = str(rule.get("field", ""))
    if not field_name:
        return True, ""
    value = data.get(field_name)
    if "equals" in rule and value != rule["equals"]:
        return False, f"{field_name} expected {rule['equals']!r}, got {value!r}"
    if "min" in rule:
        try:
            if float(value) < float(rule["min"]):
                return False, f"{field_name} {value} below minimum {rule['min']}"
        except (TypeError, ValueError):
            return False, f"{field_name} is not numeric"
    if "max" in rule:
        try:
            if float(value) > float(rule["max"]):
                return False, f"{field_name} {value} above maximum {rule['max']}"
        except (TypeError, ValueError):
            return False, f"{field_name} is not numeric"
    if "in" in rule and value not in rule["in"]:
        return False, f"{field_name} {value!r} not in allowed set"
    if rule.get("type") == "all_certificates_min_days":
        min_days = int(rule.get("min_days", 30))
        certs = value if isinstance(value, list) else data.get("certificates", [])
        if not certs:
            return False, "no certificates found in evidence"
        for cert in certs:
            days = int(cert.get("expires_in_days", -1))
            if days < min_days:
                host = cert.get("host", "unknown")
                return False, f"certificate {host} expires in {days} days (< {min_days})"
    return True, ""


def validate_evidence(manifest: dict[str, Any], payload: dict[str, Any]) -> ValidationResult:
    """Deterministic validation — never uses AI."""
    control_id = str(manifest.get("control_id") or manifest.get("common_control", "CC-UNKNOWN"))
    technology = str(manifest.get("technology") or "Common Control")
    frameworks = tuple(manifest.get("frameworks") or ())
    rules = list((manifest.get("validation") or {}).get("rules") or [])
    if not rules:
        return ValidationResult(
            control_id=control_id,
            technology=technology,
            verdict=VERDICT_WARNING,
            control_status=CONTROL_STATUS_NEEDS_REVIEW,
            evidence_quality=0.5,
            rule_id="common_control.no_rules",
            rationale="No validation rules defined in manifest",
            frameworks=frameworks,
        )
    failures: list[str] = []
    for rule in rules:
        ok, msg = _rule_passes(payload, rule)
        if not ok and msg:
            failures.append(msg)
    if failures:
        return ValidationResult(
            control_id=control_id,
            technology=technology,
            verdict=VERDICT_FAIL,
            control_status=CONTROL_STATUS_NON_COMPLIANT,
            evidence_quality=0.2,
            rule_id="common_control.validation",
            rationale="; ".join(failures),
            frameworks=frameworks,
        )
    return ValidationResult(
        control_id=control_id,
        technology=technology,
        verdict=VERDICT_PASS,
        control_status=CONTROL_STATUS_COMPLIANT,
        evidence_quality=1.0,
        rule_id="common_control.validation",
        rationale="All deterministic validation rules passed",
        frameworks=frameworks,
    )


def _resolve_custody(
    *,
    filename: str,
    content: bytes,
    evidence_key: str,
    source_item_id: str,
    version: int,
) -> Any:
    from modules.audit_intelligence.services import evidence_custody as custody

    return custody.resolve_custody(
        source_connector="common_controls",
        source_item_id=source_item_id,
        source_url=f"file://CommonControls/{filename}",
        source_modified_at="",
        filename=filename,
        mime_type="application/json",
        evidence_key=evidence_key,
        version=version,
        content=content or None,
    )


def collect_common_control_folder(
    folder: Path,
    *,
    user: str = "scheduler",
    run_id: str = "",
    control_def: CommonControlDef | None = None,
) -> CollectionReceipt:
    slug = folder.name
    ctrl = control_def or by_slug(slug)
    receipt = CollectionReceipt(
        slug=slug,
        common_control=ctrl.name if ctrl else slug,
        control_id=ctrl.control_id if ctrl else f"CC-{slug.upper().replace('-', '_')}",
    )
    receipt.discovered = True
    try:
        manifest = load_manifest(folder)
        evidence_files = list(manifest.get("evidence_files") or ["evidence.json"])
        primary = folder / evidence_files[0]
        if not primary.is_file():
            receipt.error = f"missing evidence file: {evidence_files[0]}"
            return receipt
        payload = _load_json(primary)
        content_bytes = primary.read_bytes()
        content_text = json.dumps(payload, indent=2, sort_keys=True)
        vr = validate_evidence(manifest, payload)
        receipt.verdict = vr.verdict

        asset_id = str(manifest.get("application") or "ECS Common Controls")
        evidence_key = ai_repo.make_evidence_key(asset_id, receipt.control_id)
        source_item_id = f"common-controls/{slug}/{primary.name}"
        custody = _resolve_custody(
            filename=primary.name,
            content=content_bytes,
            evidence_key=evidence_key,
            source_item_id=source_item_id,
            version=1,
        )
        receipt.object_stored = bool(custody.stored or custody.object_uri or custody.content_hash)

        frameworks = tuple(manifest.get("frameworks") or (ctrl.frameworks if ctrl else ()))
        fcm_refs: list[dict[str, Any]] = []
        try:
            from modules.frameworks.services.common_controls_service import (
                get_common_controls_service,
            )

            fcm_refs = get_common_controls_service().resolve_fcm_references(slug)
        except Exception:  # noqa: BLE001
            fcm_refs = []
        tags = ("common_control", slug, "phase1", "scheduler")
        meta = {
            "common_control": manifest.get("common_control") or receipt.common_control,
            "common_control_slug": slug,
            "common_control_id": receipt.control_id,
            "source_type": "common_controls",
            "source_name": receipt.common_control,
            "predefined_query_ids": manifest.get("predefined_query_ids")
            or (list(ctrl.predefined_query_ids) if ctrl else []),
            "alternate_collection": manifest.get("alternate_collection")
            or (ctrl.alternate_collection if ctrl else ""),
            "collection_source": "CommonControls",
            "scheduler_run_id": run_id,
            "validation_verdict": vr.verdict,
            "framework_independent": True,
            "framework_refs": list(frameworks),
            "fcm_framework_ids": list({r.get("framework_id") for r in fcm_refs if r.get("framework_id")}),
            "fcm_reference_count": len(fcm_refs),
            "content_sha256": custody.content_hash,
        }
        artifact = ai_repo.store_evidence(
            control_id=receipt.control_id,
            content=content_text,
            technology=str(manifest.get("technology") or "Common Control"),
            asset_id=asset_id,
            frameworks=frameworks,
            run_id=run_id,
            verdict=vr.verdict,
            control_status=vr.control_status,
            evidence_quality=vr.evidence_quality,
            source="common_controls",
            filename=f"COMMON_CONTROL_{slug}.json",
            tags=tags,
            evidence_key=evidence_key,
            environment=str(manifest.get("environment") or "MVP"),
            source_connector="common_controls",
            source_item_id=source_item_id,
            source_url=f"file://CommonControls/{slug}/{primary.name}",
            mime_type="application/json",
            metadata=meta,
            custody_mode=custody.custody_mode,
            object_uri=custody.object_uri,
            content_hash_override=custody.content_hash,
            size_bytes_override=custody.size_bytes,
        )
        receipt.metadata_persisted = artifact is not None
        receipt.evidence_key = evidence_key
        receipt.collected = True

        from modules.operations.engines.evidence_repository import register_upload

        ops_record = register_upload(
            filename=f"COMMON_CONTROL_{slug}.json",
            content=content_bytes,
            uploaded_by=user,
            framework=frameworks[0] if frameworks else "Cross-Framework",
            application=asset_id,
            control=receipt.control_id,
            source_connector="common_controls",
            source_item_id=source_item_id,
            source_url=f"file://CommonControls/{slug}/{primary.name}",
            environment=str(manifest.get("environment") or "MVP"),
            mime_type="application/json",
            metadata=meta,
            custody_mode=custody.custody_mode,
        )
        if str(ops_record.get("status", "")).upper() == "DUPLICATE":
            meta["duplicate"] = True
            meta["duplicate_kind"] = ops_record.get("duplicate_kind") or "sha256"
        receipt.metadata_persisted = receipt.metadata_persisted or bool(
            ops_record.get("audit_repository_synced")
        )
        receipt.collected = receipt.collected or receipt.metadata_persisted
        from modules.shared.services.evidence_workflow_engine import enroll_collected_evidence

        enroll_collected_evidence(
            ops_record,
            source_type="common_controls",
            observation_id=receipt.observation_id or "",
        )

        if vr.verdict in (VERDICT_FAIL, VERDICT_WARNING):
            observation = obs_gen.generate_observation(
                vr,
                asset_id=asset_id,
                owner=str(manifest.get("owner") or "Platform Ops"),
                evidence_reference=artifact.evidence_id if artifact else evidence_key,
                control_name=receipt.common_control,
            )
            if observation:
                receipt.observation_id = observation.observation_id
    except Exception as exc:  # noqa: BLE001 - collector returns receipt with error
        receipt.error = f"{type(exc).__name__}: {exc}"
    return receipt


def collect_all_common_controls(*, user: str = "scheduler", run_id: str = "") -> CollectionRun:
    """Discover and collect every CommonControls folder."""
    run = CollectionRun(run_id=run_id or "CC-RUN")
    folders = discover_common_control_folders()
    run.folders_discovered = len(folders)
    slug_map = {c.slug: c for c in COMMON_CONTROLS}
    for folder in folders:
        receipt = collect_common_control_folder(
            folder,
            user=user,
            run_id=run_id,
            control_def=slug_map.get(folder.name),
        )
        run.receipts.append(receipt)
        if receipt.collected:
            run.collected += 1
        if receipt.observation_id:
            run.observations += 1
    return run
