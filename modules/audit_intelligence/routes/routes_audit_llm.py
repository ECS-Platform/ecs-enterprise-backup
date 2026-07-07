"""REST API for the ECS Audit LLM Prompt Workbench (/api/audit-llm/*).

Thin JSON wrappers over the audit-LLM services (prompt library, classifier, token
estimator, execution service, benchmark runner). Follows the house response style
and never leaks a stack trace. All heavy imports are lazy so importing this module
never breaks app startup.
"""

from __future__ import annotations

import functools
from typing import Any

from fastapi import Body
from fastapi.responses import JSONResponse


def _ok(payload: dict[str, Any] | None = None, **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {"ok": True}
    if payload:
        body.update(payload)
    body.update(extra)
    return JSONResponse(body)


def _err(message: str, status: int = 400, errors: list[Any] | None = None) -> JSONResponse:
    msg = str(message)
    return JSONResponse(
        {"ok": False, "status": "error", "message": msg,
         "errors": errors if errors is not None else [msg], "error": msg},
        status_code=status,
    )


def _safe(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - never leak a stack trace
            return _err("internal_error", status=500,
                        errors=[f"{fn.__name__}: {type(exc).__name__}"])
    return wrapper


def register_audit_llm_routes(app) -> None:
    # ---------------------------------------------------------------- prompts
    @app.get("/api/audit-llm/prompts")
    @_safe
    def api_llm_prompts(category: str = "", query_type: str = "", ram_profile: str = ""):
        from modules.audit_intelligence.llm import prompt_library as pl

        prompts = pl.list_prompts(category=category, query_type=query_type, ram_profile=ram_profile)
        return _ok(prompts=prompts, count=len(prompts), categories=pl.categories())

    @app.get("/api/audit-llm/prompts/{prompt_id}")
    @_safe
    def api_llm_prompt(prompt_id: str):
        from modules.audit_intelligence.llm import prompt_library as pl

        p = pl.get_prompt(prompt_id)
        return _ok(prompt=p) if p else _err(f"Unknown prompt: {prompt_id}", status=404)

    @app.get("/api/audit-llm/profiles")
    @_safe
    def api_llm_profiles():
        from modules.audit_intelligence.llm import prompt_library as pl

        return _ok(profiles=pl.list_profiles(),
                   token_profiles=pl.load_benchmark_profiles().get("token_profiles", {}))

    # --------------------------------------------------------------- classify
    @app.post("/api/audit-llm/classify")
    @_safe
    def api_llm_classify(payload: dict[str, Any] = Body(default_factory=dict)):
        from modules.audit_intelligence.llm import query_classifier as qc

        query = str(payload.get("query") or "")
        if not query.strip():
            return _err("query is required", status=400)
        return _ok(classification=qc.classify(query))

    # ---------------------------------------------------------- token-estimate
    @app.post("/api/audit-llm/token-estimate")
    @_safe
    def api_llm_token_estimate(payload: dict[str, Any] = Body(default_factory=dict)):
        from modules.audit_intelligence.llm import token_estimator as te

        estimate = te.estimate_prompt(
            system_prompt=str(payload.get("system_prompt") or ""),
            assembled_prompt=str(payload.get("assembled_prompt") or payload.get("text") or ""),
            expected_output_tokens=int(payload.get("expected_output_tokens", 512) or 512),
            token_profile=str(payload.get("token_profile") or "medium_8k"),
            ram_profile=str(payload.get("ram_profile") or "local_16gb_safe"),
        )
        return _ok(token_estimate=estimate)

    # ------------------------------------------------------------------ query
    @app.post("/api/audit-llm/query")
    @_safe
    def api_llm_query(payload: dict[str, Any] = Body(default_factory=dict)):
        from modules.audit_intelligence.llm import execution_service as es

        result = es.execute(
            prompt_id=str(payload.get("prompt_id") or ""),
            user_query=str(payload.get("query") or ""),
            input_variables=payload.get("input_variables") or {},
            ram_profile=str(payload.get("ram_profile") or "local_16gb_safe"),
            token_profile=str(payload.get("token_profile") or ""),
            provider_model=str(payload.get("provider_model") or ""),
            use_rag=bool(payload.get("use_rag", True)),
        )
        return _ok(result=result)

    # -------------------------------------------------------------- benchmark
    @app.post("/api/audit-llm/benchmark")
    @_safe
    def api_llm_benchmark(payload: dict[str, Any] = Body(default_factory=dict)):
        from modules.audit_intelligence.llm import benchmark_runner as br

        report = br.run_benchmark(
            prompt_ids=payload.get("prompt_ids") or None,
            category=str(payload.get("category") or ""),
            all_prompts=bool(payload.get("all_prompts", False)),
            ram_profile=str(payload.get("ram_profile") or "local_16gb_safe"),
            token_profile=str(payload.get("token_profile") or ""),
            dry_run=bool(payload.get("dry_run", True)),
        )
        return _ok(report=report)

    @app.get("/api/audit-llm/benchmark/results")
    @_safe
    def api_llm_benchmark_results(limit: int = 20):
        from pathlib import Path

        report_dir = Path(__file__).resolve().parents[3] / "reports" / "audit_llm_benchmarks"
        files: list[dict[str, Any]] = []
        if report_dir.is_dir():
            for p in sorted(report_dir.glob("*.json"), reverse=True)[: max(1, int(limit))]:
                files.append({"name": p.name, "path": str(p),
                              "modified": p.stat().st_mtime})
        return _ok(results=files, count=len(files))

    @app.post("/api/audit-llm/benchmark/export")
    @_safe
    def api_llm_benchmark_export(payload: dict[str, Any] = Body(default_factory=dict)):
        from modules.audit_intelligence.llm import benchmark_runner as br

        report = br.run_benchmark(
            prompt_ids=payload.get("prompt_ids") or None,
            category=str(payload.get("category") or ""),
            all_prompts=bool(payload.get("all_prompts", False)),
            ram_profile=str(payload.get("ram_profile") or "local_16gb_safe"),
            token_profile=str(payload.get("token_profile") or ""),
            dry_run=bool(payload.get("dry_run", True)),
        )
        written = br.export_report(report)
        return _ok(written=written, summary=report["summary"])
