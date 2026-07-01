"""ECS Benchmark — additive demo route (mock/simulation only).

Renders a single, self-contained page that SIMULATES how ECS benchmark
execution and capacity-planning evidence would look inside the platform.

IMPORTANT — this module is demo-safe by design:
  * It does NOT run any benchmark, Docker, Ollama, PGVector, embeddings, or RAG.
  * It performs NO heavy backend work — the route only renders a template.
  * The execution timeline / progress / result numbers are produced entirely in
    the browser (JavaScript setTimeout) using deterministic mock data.
  * Real benchmark scripts remain untouched under scripts/ and their evidence
    under benchmark_outputs/ — this page neither imports nor invokes them.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse

from app import ecs_state
from modules.shared.services.enterprise_context import enterprise_widgets_context


def register_ecs_benchmark_routes(app, templates):
    @app.get("/mvp/ecs-benchmark", response_class=HTMLResponse)
    def mvp_ecs_benchmark(request: Request, role: str = "owner", user: str = "User", notice: str = ""):
        # Lightweight context only — no benchmark engine, no I/O, no LLM calls.
        ctx = {
            "frameworks": ecs_state.frameworks.keys(),
            "role": role,
            "user": user,
            "notice": notice,
            "scheduler_data": ecs_state.scheduler_data,
            "rejected_controls": ecs_state.rejected_controls,
            "applications": ecs_state.onboarded_applications,
        }
        # Sets nav_module="ecs_benchmark" so the left-nav item highlights.
        ctx.update(enterprise_widgets_context(role, page_module="ecs_benchmark", user=user))
        try:
            from app.auth.demo import demo_mode

            ctx["demo_mode"] = demo_mode()
        except Exception:  # noqa: BLE001 - theme flag must never break the page
            ctx["demo_mode"] = False
        return templates.TemplateResponse(request, "mvp_ecs_benchmark.html", ctx)
