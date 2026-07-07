"""Scoped tests for the ECS Audit LLM Prompt Workbench.

Fully offline + deterministic: NO local LLM, NO network, NO container required.
LLM execution is exercised only via the dry-run RAM profile (no provider call) and
via a fallback path. Covers prompt library + validation, benchmark profiles, query
classification + entity extraction, deterministic router, token estimator + RAM
compatibility, execution service (dry-run + fallback), benchmark runner + export,
and the /api/audit-llm/* endpoints.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from modules.audit_intelligence.llm import (
    benchmark_runner,
    deterministic_router,
    execution_service,
    prompt_library,
    query_classifier,
    token_estimator,
)

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Prompt library + validation
# --------------------------------------------------------------------------- #
def test_prompt_library_loads_40_prompts():
    lib = prompt_library.load_prompt_library(force=True)
    assert lib["count"] == 40
    assert not lib["errors"], f"validation errors: {lib['errors']}"


def test_prompt_library_required_fields_present():
    for p in prompt_library.list_prompts():
        for field in prompt_library.REQUIRED_FIELDS:
            assert field in p, f"{p.get('prompt_id')} missing {field}"
        assert p["query_type"] in prompt_library.VALID_QUERY_TYPES
        assert p["token_profile"] in prompt_library.VALID_TOKEN_PROFILES


def test_prompt_library_ram_filter():
    only16 = prompt_library.list_prompts(ram_profile="local_16gb_safe")
    only20 = prompt_library.list_prompts(ram_profile="local_20gb_extended")
    # 20 GB supports at least as many as 16 GB (some prompts are 20 GB-only).
    assert len(only20) >= len(only16)
    # The two worst-case dry-run prompts are not 16 GB-supported.
    ids16 = {p["prompt_id"] for p in only16}
    assert "enterprise_evidence_gap_summary" not in ids16


def test_benchmark_profiles_are_exactly_three():
    profs = {p["id"] for p in prompt_library.list_profiles()}
    assert profs == {"local_16gb_safe", "local_20gb_extended", "worst_case_enterprise_dry_run"}


def test_token_profile_context_budgets():
    assert prompt_library.token_profile_context("small_4k") == 4096
    assert prompt_library.token_profile_context("medium_8k") == 8192
    assert prompt_library.token_profile_context("extended_20k") == 20480


# --------------------------------------------------------------------------- #
# Query classifier + entity extraction
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("query,expected", [
    ("How many observations are open?", "deterministic"),
    ("How many high-risk observations exist?", "deterministic"),
    ("Which observations are older than 90 days?", "deterministic"),
    ("What are the chances observations will not be raised this year?", "llm_assisted"),
    ("Which controls are likely to fail?", "llm_assisted"),
    ("What is the likelihood of audit escalation?", "llm_assisted"),
    ("What are common root causes for delayed closure?", "llm_assisted"),
    ("Generate an executive summary of current audit readiness.", "hybrid"),
    ("Summarize all open observations for Mobile Banking.", "hybrid"),
])
def test_classify_query_types(query, expected):
    assert query_classifier.classify(query)["query_type"] == expected


def test_classify_extracts_entities():
    e = query_classifier.classify(
        "What are the chances my C-SITE observations will not be raised on Net Banking this year?"
    )["entities"]
    assert e["application"] == "Net Banking"
    assert e["framework"] in ("C-SITE", "CSITE")
    assert e["date_range"]


def test_classify_empty_is_unsupported():
    assert query_classifier.classify("")["query_type"] == "unsupported"


def test_classify_hybrid_when_both_signals():
    r = query_classifier.classify("How many high-risk observations are open, and summarize the business impact?")
    assert r["query_type"] == "hybrid"


# --------------------------------------------------------------------------- #
# Deterministic router
# --------------------------------------------------------------------------- #
def test_router_open_observations_returns_structured_result():
    r = deterministic_router.open_observations_by_application("Net Banking")
    assert "answer_text" in r and isinstance(r["count"], int)
    assert r["data_used"] and r["source_references"]


def test_router_high_risk_observations():
    r = deterministic_router.high_risk_observations()
    assert isinstance(r["count"], int)
    assert "by_framework" in r


def test_router_aging_observations_bounded():
    r = deterministic_router.aging_observations(min_age_days=90)
    assert r["min_age_days"] == 90
    assert isinstance(r["rows"], list)


def test_router_framework_highest_gap():
    r = deterministic_router.framework_highest_gap()
    assert "highest_gap_framework" in r


def test_router_build_deterministic_context_never_raises():
    for pid in ("observation_count", "csite_closure_probability", "unknown_prompt_id"):
        r = deterministic_router.build_deterministic_context(pid, {"application": "Net Banking"})
        assert "answer_text" in r


# --------------------------------------------------------------------------- #
# Token estimator + RAM compatibility
# --------------------------------------------------------------------------- #
def test_token_estimate_basic():
    est = token_estimator.estimate_prompt(
        system_prompt="a" * 400, assembled_prompt="b" * 800,
        expected_output_tokens=256, token_profile="small_4k", ram_profile="local_16gb_safe")
    assert est["input_tokens"] > 0
    assert est["total_tokens"] == est["input_tokens"] + 256
    assert est["context_budget"] == 4096


def test_ram_compatibility_16gb_blocks_20k():
    compat = token_estimator.ram_profile_compatibility("local_16gb_safe", "extended_20k")
    assert compat["blocked"] is True
    assert compat["allowed"] is False


def test_ram_compatibility_16gb_restricts_16k():
    compat = token_estimator.ram_profile_compatibility("local_16gb_safe", "large_16k")
    assert compat["allowed"] is True
    assert compat["restricted"] is True


def test_ram_compatibility_20gb_allows_20k_restricted():
    compat = token_estimator.ram_profile_compatibility("local_20gb_extended", "extended_20k")
    assert compat["allowed"] is True
    assert compat["restricted"] is True


def test_ram_compatibility_dry_run_mode():
    compat = token_estimator.ram_profile_compatibility("worst_case_enterprise_dry_run", "worst_case_enterprise_dry_run")
    assert compat["execution_mode"] == "dry_run"


# --------------------------------------------------------------------------- #
# Execution service (dry-run + fallback; no live LLM)
# --------------------------------------------------------------------------- #
def test_execute_dry_run_no_llm_call():
    r = execution_service.execute(
        prompt_id="enterprise_evidence_gap_summary",
        user_query="Summarize enterprise evidence gaps",
        ram_profile="worst_case_enterprise_dry_run",
        token_profile="worst_case_enterprise_dry_run",
    )
    assert r["execution_mode"] == "dry_run"
    assert r["fallback_used"] is True
    assert r["llm_response"] == ""            # dry-run: no LLM text
    assert r["deterministic_result"]["answer_text"]
    assert r["token_estimate"]["total_tokens"] > 0


def test_execute_llm_assisted_includes_confidence_scaffold():
    r = execution_service.execute(
        prompt_id="csite_closure_probability",
        user_query="What are the chances C-SITE observations will not be raised on Net Banking this year?",
        ram_profile="worst_case_enterprise_dry_run",   # dry-run -> no live call, deterministic
        token_profile="large_16k",
    )
    assert r["query_type"] == "llm_assisted"
    assert r["confidence"]           # scaffolded
    assert r["assumptions"] and r["limitations"]


def test_execute_llm_fallback_when_provider_unavailable(monkeypatch):
    # Force the provider factory to raise so the execute path takes the fallback
    # branch (no crash, deterministic result preserved, clear fallback message).
    import ecs_platform.llm_engine as engine

    def _boom(*a, **k):
        raise engine.LLMError("provider unavailable in test")

    monkeypatch.setattr(engine, "get_provider", _boom)
    r = execution_service.execute(
        prompt_id="observation_count",
        user_query="How many observations are open in Net Banking?",
        ram_profile="local_16gb_safe", token_profile="small_4k",
    )
    assert r["fallback_used"] is True
    assert r["deterministic_result"]["answer_text"]
    assert "FALLBACK" in r["llm_response"]


def test_execute_deterministic_result_not_altered():
    r = execution_service.execute(
        prompt_id="observation_count",
        user_query="How many observations are open in Net Banking?",
        ram_profile="worst_case_enterprise_dry_run", token_profile="small_4k",
    )
    assert "Net Banking" in r["deterministic_result"]["answer_text"]


# --------------------------------------------------------------------------- #
# Benchmark runner + export
# --------------------------------------------------------------------------- #
def test_benchmark_dry_run_report():
    report = benchmark_runner.run_benchmark(
        category="executive", ram_profile="local_16gb_safe", dry_run=True)
    assert report["effective_mode"] == "dry_run"
    assert report["summary"]["prompts_run"] >= 1
    for r in report["results"]:
        assert r["total_estimated_tokens"] >= 0


def test_benchmark_export_writes_files(tmp_path):
    report = benchmark_runner.run_benchmark(
        prompt_ids=["observation_count"], ram_profile="local_16gb_safe", dry_run=True)
    written = benchmark_runner.export_report(report, out_dir=tmp_path)
    assert "md" in written and "json" in written
    assert Path(written["md"]).is_file() and Path(written["json"]).is_file()
    assert "ECS Audit LLM Benchmark Report" in Path(written["md"]).read_text(encoding="utf-8")


def test_benchmark_20gb_profile_runs():
    report = benchmark_runner.run_benchmark(
        prompt_ids=["framework_gap_analysis"], ram_profile="local_20gb_extended", dry_run=True)
    assert report["summary"]["prompts_run"] == 1


# --------------------------------------------------------------------------- #
# API endpoints
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, follow_redirects=False)


_Q = "?role=owner&user=U"


def test_api_prompts(client):
    r = client.get("/api/audit-llm/prompts" + _Q)
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True and body["count"] == 40
    assert body["categories"]


def test_api_profiles(client):
    r = client.get("/api/audit-llm/profiles" + _Q)
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["profiles"]}
    assert ids == {"local_16gb_safe", "local_20gb_extended", "worst_case_enterprise_dry_run"}


def test_api_classify(client):
    r = client.post("/api/audit-llm/classify" + _Q,
                    json={"query": "How many high-risk observations are open?"})
    assert r.status_code == 200 and r.json()["classification"]["query_type"] == "deterministic"


def test_api_classify_requires_query(client):
    r = client.post("/api/audit-llm/classify" + _Q, json={})
    assert r.status_code == 400 and r.json()["ok"] is False


def test_api_token_estimate(client):
    r = client.post("/api/audit-llm/token-estimate" + _Q,
                    json={"text": "x" * 4000, "token_profile": "small_4k", "ram_profile": "local_16gb_safe"})
    assert r.status_code == 200
    assert r.json()["token_estimate"]["input_tokens"] > 0


def test_api_query_dry_run(client):
    r = client.post("/api/audit-llm/query" + _Q, json={
        "prompt_id": "observation_count", "query": "How many observations are open in Net Banking?",
        "ram_profile": "worst_case_enterprise_dry_run"})
    assert r.status_code == 200
    res = r.json()["result"]
    assert res["deterministic_result"]["answer_text"]
    assert res["execution_mode"] == "dry_run"


def test_api_benchmark_dry_run(client):
    r = client.post("/api/audit-llm/benchmark" + _Q,
                    json={"category": "observations", "ram_profile": "local_16gb_safe", "dry_run": True})
    assert r.status_code == 200
    assert r.json()["report"]["summary"]["prompts_run"] >= 1


def test_api_unknown_prompt_404(client):
    r = client.get("/api/audit-llm/prompts/nope" + _Q)
    assert r.status_code == 404


def test_ui_workbench_page_renders(client):
    r = client.get("/mvp/audit/llm-workbench" + _Q)
    assert r.status_code == 200
    assert "Audit LLM Prompt Workbench" in r.text
    assert "local_16gb_safe" in r.text and "local_20gb_extended" in r.text


def test_no_secrets_or_ips_in_configs():
    import re
    for rel in ("config/audit_llm_prompt_library.yaml", "config/audit_llm_benchmark_profiles.yaml"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        for ip in re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", text):
            assert ip.startswith(("127.", "0.0.0.0")), f"public IP in {rel}: {ip}"
        assert not re.search(r"(api[_-]?key|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9/+=_-]{16,}", text, re.I)
