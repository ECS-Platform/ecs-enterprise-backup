"""AI Ops Assistant summary drill pages — Business, Technical, Executive views."""

from __future__ import annotations

from modules.shared.utils.demo_data_standards import DRILL_COLUMNS, ensure_drill_rows, generate_standard_drill_row
from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS

SUMMARY_PAGE_MODES = ("business", "technical", "executive", "audit", "compliance", "evidence", "incident", "root_cause")

RECOMMENDATIONS = {
    "business": [
        "Issue customer advisory on login delays and transaction confirmation times",
        "Escalate to business continuity coordinator for retail channel impact",
        "Prepare regulator notification draft if outage exceeds 4 hours",
    ],
    "technical": [
        "Validate DB replication and failover consistency on CBS cluster",
        "Close Tripwire baseline drift on authentication middleware",
        "Expedite ITPP DR validation and incident timeline evidence upload",
    ],
    "executive": [
        "Brief CIO steering on moderate customer impact with no data compromise",
        "Track PCI DSS and RBI Cyber incident reporting thresholds",
        "Monitor compensating controls for active TD exception on failover cluster",
    ],
}


def _scenario_rows(scenario: dict, scenario_key: str, mode: str) -> list[dict]:
    app = scenario["application"]
    base = []
    for i, sig in enumerate(scenario.get("correlated_signals", [])[:8]):
        base.append({
            "application": app,
            "framework": "ITPP" if "DR" in sig or "ITPP" in sig else pick_fw(sig),
            "domain": "Operations",
            "control": scenario.get("governance_observations", ["—"])[i % max(len(scenario.get("governance_observations", [1])), 1)],
            "owner": "Infrastructure Lead" if i % 2 else "App Owner",
            "status": scenario["status"],
            "risk": scenario["severity"],
            "evidence": f"INC-EVD-{scenario_key[:3].upper()}-{i:03d}",
            "finding": sig,
            "date": scenario.get("timeline", [["2026-05-24", ""]])[min(i, len(scenario.get("timeline", [])) - 1)][0],
        })
    for obs in scenario.get("governance_observations", []):
        base.append(generate_standard_drill_row(len(base), metric=mode, application=app))
        base[-1]["finding"] = obs
        base[-1]["control"] = obs[:60]
    for action in scenario.get("recommended_actions", []):
        base.append(generate_standard_drill_row(len(base), metric=mode, application=app))
        base[-1]["finding"] = f"Recommendation: {action}"
    return ensure_drill_rows(base, 25, metric=mode)


def pick_fw(text: str) -> str:
    for fw in ("PCI DSS", "DPSC", "VAPT", "DB Baselining", "ITPP", "AppSec"):
        if fw.lower() in text.lower():
            return fw
    return "Enterprise-wide"


# ---------------------------------------------------------------------------
# LLM-generated narrative (additive, optional). build_summary_page() above stays
# fully deterministic/templated — this is a separate, fail-soft layer consumed
# via a secondary AJAX call (see /mvp/api/ai-ops-summary-narrative) so a slow or
# unreachable model never blocks or breaks the summary page itself.
# ---------------------------------------------------------------------------

# Anti-hallucination refusal, mirroring ecs_platform.rag.NO_EVIDENCE_MESSAGE: shown
# when a page has no grounding data to narrate rather than letting the model guess.
NO_SCENARIO_DATA_MESSAGE = "Insufficient scenario data to generate a narrative."

_NARRATIVE_SYSTEM_PROMPT = (
    "You are the ECS AI Ops Assistant, writing a short narrative for one perspective "
    "of an active incident summary page. Rules:\n"
    "1. Use ONLY the supplied scenario facts (situation, related applications, related "
    "frameworks, recommended actions, sample findings). Never invent tickets, systems, "
    "figures, or facts not given.\n"
    "2. Write 2-4 concise, audit-ready sentences addressed to the stated audience.\n"
    "3. Do not include chain-of-thought or <think> sections; output only the final narrative.\n"
)


def _build_narrative_prompt(page: dict) -> str:
    lines = [f"Perspective: {page['title']}", f"Situation: {page.get('subtitle', '')}"]
    if page.get("related_applications"):
        lines.append("Related applications: " + ", ".join(page["related_applications"]))
    if page.get("related_frameworks"):
        lines.append("Related frameworks: " + ", ".join(page["related_frameworks"]))
    if page.get("related_controls"):
        lines.append("Related controls: " + ", ".join(page["related_controls"][:5]))
    if page.get("recommendations"):
        lines.append("Recommended actions:\n" + "\n".join(f"- {r}" for r in page["recommendations"]))
    findings = [r.get("finding", "") for r in page.get("rows", [])[:5] if r.get("finding")]
    if findings:
        lines.append("Sample findings:\n" + "\n".join(f"- {f}" for f in findings))
    lines.append("\nWrite the narrative for this perspective now.")
    return "\n".join(lines)


# Ollama's default keep_alive=0s (config/llm.yaml) unloads qwen3:8b after every
# call, so the first narrative request in a while pays the full model-load cost
# (weights into RAM) on top of generation. That load can be slow/flaky enough to
# fail outright (connection reset while Ollama is still initializing the runner)
# even though a request moments later — once the model is resident — succeeds
# immediately. Retrying in-process with a short backoff absorbs that one-shot
# cold-start failure so the caller never sees it.
_NARRATIVE_RETRY_BACKOFF_SECONDS = (1.5, 3.0)  # len() = number of retries after the first attempt


def generate_narrative(page: dict) -> dict:
    """LLM-generated narrative for one AI-Ops summary perspective, grounded in `page`.

    Fails soft on every path (no configured provider, unreachable provider, empty
    response): returns grounded=False with an empty narrative so the caller keeps
    showing the deterministic ``page['recommendations']`` text unchanged — this never
    raises and never turns into a 500, matching every other I/O path in ECS (e.g.
    ecs_platform.rag.answer()). Uses get_provider() so the model stays swappable via
    config/llm.yaml; does not touch the provider's global keep_alive setting.

    Retries the generation call itself (not the whole function) up to
    ``len(_NARRATIVE_RETRY_BACKOFF_SECONDS)`` times with a short backoff — this is
    purely a cold-model-load absorber and stays invisible to the caller: only the
    final attempt's failure detail is surfaced if every attempt fails.
    """
    if not page.get("rows") and not page.get("recommendations"):
        return {"ok": True, "grounded": False, "narrative": NO_SCENARIO_DATA_MESSAGE, "source": "refused"}

    try:
        from ecs_platform.llm_engine.provider import get_provider

        provider = get_provider()
        if not provider.configured():
            return {"ok": True, "grounded": False, "narrative": "", "source": "fallback",
                    "detail": "LLM provider not configured"}
        prompt = _build_narrative_prompt(page)
    except Exception as exc:  # noqa: BLE001 - fail soft; page must never break on this
        return {"ok": True, "grounded": False, "narrative": "", "source": "fallback", "detail": str(exc)}

    import time as _time

    last_detail = "empty model response"
    for attempt, backoff in enumerate((0.0, *_NARRATIVE_RETRY_BACKOFF_SECONDS)):
        if backoff:
            _time.sleep(backoff)
        try:
            text, usage = provider.generate_with_metadata(prompt, system=_NARRATIVE_SYSTEM_PROMPT)
            text = text.strip()
            if text:
                return {"ok": True, "grounded": True, "narrative": text, "source": "llm",
                        "model": provider.model,
                        "provider": type(provider).__name__.replace("Provider", "").lower(),
                        "usage": usage}
        except Exception as exc:  # noqa: BLE001 - fail soft; page must never break on this
            last_detail = str(exc)
    return {"ok": True, "grounded": False, "narrative": "", "source": "fallback", "detail": last_detail}


def build_summary_page(mode: str, scenario_key: str = "net_banking", role: str = "cio") -> dict | None:
    if mode not in SUMMARY_PAGE_MODES:
        return None
    scenario = OUTAGE_SCENARIOS.get(scenario_key) or OUTAGE_SCENARIOS.get("net_banking")
    titles = {
        "business": "Business Summary",
        "technical": "Technical Summary",
        "executive": "Executive Summary",
        "audit": "Audit Summary",
        "compliance": "Compliance Summary",
        "evidence": "Evidence Summary",
        "incident": "Incident Summary",
        "root_cause": "Root Cause Analysis",
    }
    rows = _scenario_rows(scenario, scenario_key, mode)
    related_apps = list({r["application"] for r in rows}) + scenario.get("impacted_apps", [])
    related_fws = list({r["framework"] for r in rows if r["framework"] != "Enterprise-wide"})
    return {
        "title": f"{titles.get(mode, mode.title())} — {scenario['application']}",
        "subtitle": scenario.get("customer_impact", ""),
        "mode": mode,
        "scenario_key": scenario_key,
        "scenario": scenario,
        "columns": [{"key": c, "label": c.replace("_", " ").title(), "wrap": c in ("application", "control", "finding")} for c in DRILL_COLUMNS],
        "rows": rows,
        "recommendations": RECOMMENDATIONS.get(mode, scenario.get("recommended_actions", [])),
        "related_applications": related_apps[:8],
        "related_frameworks": related_fws[:8],
        "related_controls": [r["control"] for r in rows[:8]],
        "role": role,
    }
