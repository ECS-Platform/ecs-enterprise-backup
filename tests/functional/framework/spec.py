"""Case registration: every workbook Functional Test ID is bound to ONE orchestration function.

    @case("UC01-FT001", framework="scheduler", capability="create_schedule",
          component="POST /mvp/platform/scheduler", data="DataFactory.schedule")
    def uc01_ft001(ctx): ...

``CASES``/``META`` feed (a) the pytest runner (``run_case``) and (b) the traceability generator. Use-case modules contain only
orchestration; all behaviour lives in the helpers (see framework/*.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

CaseFn = Callable[["FunctionalContext"], None]  # noqa: F821 - forward ref


@dataclass(frozen=True)
class CaseMeta:
    id: str
    framework: str            # reusable helper group (scheduler, evidence, dashboard ...)
    capability: str           # concrete capability exercised (create_schedule, hash_verify ...)
    component: str            # ECS API route / UI page / table / service the case targets
    data: str = ""            # test-data source
    kind: str = "specific"    # specific | crosscutting


CASES: dict[str, CaseFn] = {}
META: dict[str, CaseMeta] = {}


def register(case_id: str, fn: CaseFn, meta: CaseMeta) -> None:
    if case_id in CASES:
        raise ValueError(f"duplicate registration for {case_id}")
    CASES[case_id] = fn
    META[case_id] = meta


def case(case_id: str, *, framework: str, capability: str, component: str, data: str = "") -> Callable[[CaseFn], CaseFn]:
    def deco(fn: CaseFn) -> CaseFn:
        register(case_id, fn, CaseMeta(case_id, framework, capability, component, data))
        return fn

    return deco


@dataclass
class UseCaseProfile:
    """What the generic cross-cutting scenarios need to know about a use case's real ECS surface."""
    uc: str
    subject: str
    page: str                                   # primary HTML page
    api: str = ""                               # primary read-only JSON endpoint ("" if none)
    api_params: dict[str, Any] = field(default_factory=dict)
    dashboard_api: str = ""                     # JSON endpoint behind dashboards/reports for this UC
    rbac_capability: str = "upload_evidence"    # key in test_data.yaml rbac_expectations
    perf_key: str = "default_response_p95_ms"
    view_personas: tuple[str, ...] = ("owner", "auditor", "cio", "compliance_head")
    # callables (ctx)->ApiResponse for UC-specific triggers; None -> the shared evidence upload flow
    trigger: Callable[[Any], Any] | None = None
    notice_contains: str = "uploaded"
    audit_action: str = "upload"
    integration_source: str = "upload"          # upload | scheduler


def run_case(case_id: str, ctx) -> None:
    from ..usecases import ensure_loaded

    ensure_loaded()
    if case_id not in CASES:
        raise KeyError(f"No automation registered for {case_id}")
    ctx.case_id = case_id
    CASES[case_id](ctx)
