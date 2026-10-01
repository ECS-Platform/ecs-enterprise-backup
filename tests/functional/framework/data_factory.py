"""Deterministic test-data factory. No production data; every artefact name carries the run prefix.

Determinism: names/contents derive from (seed, run_id, counter) via sha256, so two runs with the same
``ECS_FT_SEED`` and ``ECS_FT_RUN_ID`` produce identical data. Catalogue values (application/framework) come from config.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from .config import FunctionalConfig


@dataclass
class TestFile:
    __test__ = False  # not a pytest test class
    name: str
    content: bytes
    mime: str = "text/plain"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()

    def as_upload(self, field_name: str = "files") -> tuple[str, tuple[str, bytes, str]]:
        return field_name, (self.name, self.content, self.mime)


@dataclass
class DataFactory:
    cfg: FunctionalConfig
    run_id: str = field(default_factory=lambda: os.environ.get("ECS_FT_RUN_ID", "r0"))
    _n: int = 0

    # ---- primitives ------------------------------------------------------------------------------------
    @property
    def prefix(self) -> str:
        return str(self.cfg.test_data.get("run_prefix", "FT"))

    @property
    def rng(self) -> random.Random:
        return random.Random(f"{self.cfg.test_data.get('seed', 1)}-{self.run_id}")

    def _next(self) -> int:
        self._n += 1
        return self._n

    def unique(self, label: str = "x") -> str:
        h = hashlib.sha256(f"{self.cfg.test_data.get('seed')}-{self.run_id}-{label}-{self._next()}".encode()).hexdigest()[:8]
        return f"{self.prefix}-{label}-{h}"

    # ---- catalogue ----------------------------------------------------------------------------------------
    def application(self, second: bool = False) -> str:
        c = self.cfg.catalog
        return c["second_application"] if second else c["default_application"]

    def framework(self, second: bool = False) -> str:
        c = self.cfg.catalog
        return c["second_framework"] if second else c["default_framework"]

    def control(self) -> str:
        return str(self.cfg.catalog.get("default_control") or "")

    # ---- files / evidence ------------------------------------------------------------------------------------
    def file(self, kind: str = "valid_text", *, unique: bool = True, body: str | None = None) -> TestFile:
        spec = self.cfg.test_data["files"][kind]
        base, _, ext = spec["name"].rpartition(".")
        name = f"{base}_{self.unique('f').split('-')[-1]}.{ext}" if unique else spec["name"]
        if kind == "empty":
            content = b""
        elif body is not None:
            content = body.encode()
        elif spec["mime"] == "application/json":
            content = json.dumps({"run": self.run_id, "nonce": self.unique("j"), "control_check": "ok"}, sort_keys=True).encode()
        elif spec["mime"] == "text/csv":
            content = f"id,value\n{self.unique('c')},1\n".encode()
        else:
            content = f"ECS functional test evidence {self.unique('t')}\n".encode()
        return TestFile(name=name, content=content, mime=spec["mime"])

    def files(self, n: int, kind: str = "valid_text") -> list[TestFile]:
        return [self.file(kind) for _ in range(n)]

    def duplicate_of(self, f: TestFile) -> TestFile:
        return TestFile(name=f.name, content=f.content, mime=f.mime)

    def new_version_of(self, f: TestFile) -> TestFile:
        return TestFile(name=f.name, content=f.content + f"\nrevision {self.unique('v')}\n".encode(), mime=f.mime)

    def evidence_metadata(self, **overrides: Any) -> dict[str, Any]:
        """Form fields accepted by ECS POST /evidence/upload (modules/shared/routes/evidence_routes.py)."""
        base = {"framework": self.framework(), "application": self.application(), "control": self.control(),
                "evidence_type": self.cfg.catalog.get("evidence_type", "Document"),
                "audit_cycle": self.cfg.catalog.get("audit_cycle", "Q2 2026"), "comments": f"{self.prefix} functional test",
                "owner": ""}
        base.update(overrides)
        return base

    def metadata(self, **overrides: Any) -> dict[str, Any]:
        return self.evidence_metadata(**overrides)

    # ---- other categories --------------------------------------------------------------------------------------
    def schedule(self, **overrides: Any) -> dict[str, Any]:
        """Fields of ECS POST /mvp/platform/scheduler (name, connector, app_slug, frequency, owner)."""
        base = {"name": self.unique("sched"), "connector": self.cfg.catalog["connectors"]["scheduler_default"],
                "app_slug": self.application().lower().replace(" ", "-"), "frequency": "Daily", "owner": ""}
        base.update(overrides)
        return base

    def connector(self, kind: str = "sharepoint") -> str:
        return self.cfg.catalog["connectors"].get(kind, kind)

    def application_record(self, **overrides: Any) -> dict[str, Any]:
        """Fields of ECS POST /mvp/platform/onboarding."""
        base = {"name": self.unique("app"), "description": "functional test application", "owner": "AppOwner",
                "owner_email": f"{self.prefix.lower()}-owner@example.test", "business_unit": "Retail",
                "criticality": "Medium", "environment": "Production", "lifecycle_status": "Active",
                "tech_stack": "Python", "hosting": "On-Prem", "frameworks": self.framework()}
        base.update(overrides)
        return base

    def user_role(self, persona: str = "auditor") -> dict[str, str]:
        p = self.cfg.personas[persona]
        return {"persona": persona, "role": p["login_role"], "user": p["user"]}

    def report_request(self, report_id: str = "", fmt: str = "pdf") -> dict[str, str]:
        return {"report_id": report_id, "format": fmt, "framework": self.framework(), "application": self.application()}

    def notification_text(self) -> str:
        return self.unique("notify")

    def compliance_observation(self, **overrides: Any) -> dict[str, Any]:
        base = {"title": self.unique("obs"), "description": "functional test observation", "severity": "Medium",
                "framework": self.framework(), "control_id": self.control() or "CTRL-FT", "application_id": self.application()}
        base.update(overrides)
        return base

    def reporting_period(self, days: int = 30) -> tuple[str, str]:
        end = date(2026, 1, 31)
        return (end - timedelta(days=days)).isoformat(), end.isoformat()

    def prompt(self, kind: str = "evidence") -> str:
        return {"evidence": "Which evidence exists for access review controls?",
                "no_answer": "What is the recipe for ECS_FT_NONEXISTENT_TOPIC_zzz?",
                "followup": "And for the same application?"}[kind]
