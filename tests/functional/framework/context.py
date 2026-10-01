"""FunctionalContext: one object handed to every case, wiring all reusable helpers over a single API client.

Construction is cheap and performs NO network I/O; connections (DB, object store, browser) open lazily on first use.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from .ai import AiHelper
from .api_client import ApiResponse, EcsApiClient
from .audit import AuditHelper
from .config import FunctionalConfig, load_config
from .connectors import ConnectorHelper
from .correlation import CorrelationTracker
from .dashboard import ComplianceHelper, DashboardHelper, ReportingHelper, SearchHelper
from .data_factory import DataFactory
from .db import EcsDatabase
from .errors import CapabilityBlocked
from .evidence import EvidenceHelper
from .lifecycle import LifecycleHelper, OnboardingHelper
from .notification import NotificationHelper
from .scheduler import SchedulerHelper
from .security import ConcurrencyHelper, PerformanceHelper, RbacHelper, SecurityHelper
from .storage import ObjectStoreHelper


class FunctionalContext:
    def __init__(self, cfg: FunctionalConfig | None = None, persona: str = "owner") -> None:
        self.cfg = cfg or load_config()
        self.api = EcsApiClient(self.cfg, persona=persona)
        self.data = DataFactory(self.cfg)
        self.correlation = CorrelationTracker()
        self.db = EcsDatabase(self.cfg)
        self.storage = ObjectStoreHelper(self.cfg)
        self.evidence = EvidenceHelper(self.api, self.data)
        self.scheduler = SchedulerHelper(self.api, self.data, self.db)
        self.connectors = ConnectorHelper(self.api, self.data)
        self.audit = AuditHelper(self.api, self.db)
        self.notifier = NotificationHelper(self.api, self.audit)
        self.dashboard = DashboardHelper(self.api, self.data)
        self.search = SearchHelper(self.api)
        self.compliance = ComplianceHelper(self.api, self.data)
        self.reporting = ReportingHelper(self.api, self.data)
        self.ai = AiHelper(self.api, self.data)
        self.lifecycle = LifecycleHelper(self.api, self.data, self.db)
        self.onboarding = OnboardingHelper(self.api, self.data, self.db)
        self.rbac = RbacHelper(self.api)
        self.security = SecurityHelper(self.api, self.db)
        self.concurrency = ConcurrencyHelper(self.api)
        self.perf = PerformanceHelper(self.api)
        self.ui_session: Any = None   # set lazily via ui()
        self.steps: list[str] = []
        self.case_id: str = ""

    # ---- persona / tracking -----------------------------------------------------------------------------------------
    def as_persona(self, persona: str) -> EcsApiClient:
        return self.api.as_persona(persona)

    def track(self, resp: ApiResponse) -> ApiResponse:
        """Record correlation identifiers from a response (request_id, run_id, evidence_id ...)."""
        self.correlation.from_response(resp)
        return resp

    @contextmanager
    def step(self, description: str) -> Iterator[None]:
        self.steps.append(description)
        yield

    # ---- gating (CapabilityBlocked -> pytest skip with reason) -------------------------------------------------------
    def require_mutation(self) -> None:
        if not self.cfg.feature("mutating_tests"):
            raise CapabilityBlocked("Test creates/updates ECS data; enable with ECS_FT_ALLOW_MUTATION=true on a non-production ECS.",
                                    requires="mutating_tests flag")

    def require_db(self) -> None:
        if not self.db.enabled:
            raise CapabilityBlocked("Database validation disabled (ECS_FT_DB_ENABLED=true + ECS_REPO_PG_* env).", requires="PostgreSQL access")

    def require_destructive(self) -> None:
        if not self.cfg.feature("destructive_tests"):
            raise CapabilityBlocked("Destructive/retention scenario disabled (ECS_FT_ALLOW_DESTRUCTIVE=true).", requires="destructive_tests flag")

    def require_restart_hook(self) -> None:
        if not self.cfg.get("hooks.restart_command"):
            raise CapabilityBlocked("ECS exposes no restart API; set ECS_FT_RESTART_CMD to a harness command that restarts the "
                                    "ECS process and waits for /healthz.", requires="restart hook")

    def restart_ecs(self) -> None:
        """Run the configured restart command (harness-owned), then wait for /healthz. Never invoked at import."""
        import subprocess

        from .wait import wait_until

        self.require_restart_hook()
        subprocess.run(str(self.cfg.get("hooks.restart_command")), shell=True, check=True, timeout=self.cfg.long_timeout)  # noqa: S602
        wait_until(lambda: self.api.get("/healthz", anonymous=True).status == 200, timeout=self.cfg.long_timeout,
                   interval=self.cfg.poll_interval, what="ECS /healthz after restart")

    def require_live_connectors(self) -> None:
        if not self.cfg.feature("live_connectors"):
            raise CapabilityBlocked("Live connector traffic disabled (ECS_FT_LIVE_CONNECTORS=true and connector credentials).",
                                    requires="live_connectors flag")

    # ---- UI ---------------------------------------------------------------------------------------------------------
    def ui(self, persona: str | None = None):
        from .ui.browser import UiSession
        from .evidence_capture import REPORTS_DIR

        if self.ui_session is None:
            self.ui_session = UiSession(self.cfg, REPORTS_DIR / "screenshots").start()
        if persona:
            self.ui_session.login_as(persona)
        return self.ui_session

    # ---- teardown -----------------------------------------------------------------------------------------------------
    def close(self) -> None:
        if self.ui_session is not None:
            self.ui_session.stop()
        self.db.close()
        self.api.close()
