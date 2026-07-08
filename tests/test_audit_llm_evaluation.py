"""Tests for the audit LLM evaluation suite (replay, compare, grounding, citations).

Deterministic + offline (no live LLM). Exercises the service layer and the
`/api/audit-llm/*` evaluation endpoints.
"""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from app.main import app
from modules.audit_intelligence.llm import llm_evaluation as ev

client = TestClient(app)


# --------------------------------------------------------------------------- #
# Replay (no live LLM)
# --------------------------------------------------------------------------- #
def test_replay_dry_run_no_live_llm():
    res = ev.replay({"prompt_id": "observation_count",
                     "query": "How many observations are open in Net Banking?"})
    assert res["ok"] is True
    assert res["mode"] == "dry_run"
    replayed = res["replayed"]
    # dry-run forces the no-LLM path -> fallback_used True, no provider call
    assert replayed["fallback_used"] is True
    assert "token_estimate" in replayed


def test_replay_requires_prompt_or_query():
    assert ev.replay({})["ok"] is False


def test_api_replay():
    r = client.post("/api/audit-llm/replay",
                    json={"record": {"prompt_id": "observation_count",
                                     "query": "How many high-risk observations exist?"}})
    assert r.status_code == 200
    assert r.json()["mode"] == "dry_run"


# --------------------------------------------------------------------------- #
# Compare
# --------------------------------------------------------------------------- #
def test_compare_structured_diff():
    a = {"token_estimate": {"total_tokens": 100}, "source_references": ["E1"],
         "assumptions": ["x"], "fallback_used": False, "llm_response": "net banking passes pci"}
    b = {"token_estimate": {"total_tokens": 150}, "source_references": ["E2"],
         "assumptions": ["y"], "fallback_used": True, "llm_response": "net banking fails pci"}
    d = ev.compare(a, b)
    assert d["token_estimate"]["delta_total"] == 50
    assert d["fallback_used"]["differs"] is True
    assert d["source_references"]["only_a"] == ["E1"]
    assert d["source_references"]["only_b"] == ["E2"]
    assert 0.0 <= d["response"]["jaccard"] <= 1.0


def test_compare_identical_is_jaccard_one():
    a = {"llm_response": "same text here", "token_estimate": {"total_tokens": 10}}
    d = ev.compare(a, a)
    assert d["response"]["jaccard"] == 1.0


def test_api_compare_bad_input():
    assert client.post("/api/audit-llm/compare", json={"a": 1}).status_code == 400


# --------------------------------------------------------------------------- #
# Grounding / hallucination
# --------------------------------------------------------------------------- #
def test_grounding_grounded():
    ctx = {"deterministic_result": {"answer_text":
           "Net Banking has 5 open observations for PCI DSS encryption controls"}}
    g = ev.validate_grounding("Net Banking has 5 open observations for PCI DSS encryption", ctx)
    assert g["grounding"] == "grounded"
    assert g["supported_ratio"] >= 0.6


def test_grounding_unsupported():
    ctx = {"deterministic_result": {"answer_text": "Net Banking observations for PCI DSS"}}
    g = ev.validate_grounding("The moon is made of cheese and quantum tunnels power banks", ctx)
    assert g["grounding"] == "unsupported"


def test_grounding_empty_context_is_unsupported():
    g = ev.validate_grounding("some concrete claim about servers", {})
    assert g["grounding"] == "unsupported"


def test_grounding_empty_answer():
    g = ev.validate_grounding("", {"deterministic_result": {"answer_text": "x"}})
    assert g["grounding"] == "empty_answer"


# --------------------------------------------------------------------------- #
# Citation validation
# --------------------------------------------------------------------------- #
def test_citations_valid():
    ctx = {"source_references": ["EVD-1", "EVD-2"]}
    prompt = "Evidence context:\n[E1] source=x\n[E2] source=y"
    c = ev.validate_citations("Per [E1] and [E2] the control passes", ctx, assembled_prompt=prompt)
    assert c["valid"] is True
    assert c["missing"] == []


def test_citations_missing_detected():
    ctx = {"source_references": ["EVD-1"]}
    prompt = "Evidence context:\n[E1] source=x"
    c = ev.validate_citations("Per [E5] this holds", ctx, assembled_prompt=prompt)
    assert c["valid"] is False
    assert "[E5]" in c["missing"]


def test_citations_evidence_key_detected():
    ctx = {"source_references": ["EVD-1", "EVD-2"]}
    c = ev.validate_citations("As shown in EVD-1 the control passes", ctx)
    assert "EVD-1" in c["cited_evidence_keys"]


# --------------------------------------------------------------------------- #
# evaluate() convenience + API
# --------------------------------------------------------------------------- #
def test_evaluate_over_execution_result():
    q = client.post("/api/audit-llm/query",
                    json={"prompt_id": "observation_count",
                          "query": "How many observations are open in Net Banking?",
                          "ram_profile": "worst_case_enterprise_dry_run"}).json()
    out = ev.evaluate(q)
    assert "grounding" in out and "citations" in out


def test_api_validate_grounding_with_result():
    q = client.post("/api/audit-llm/query",
                    json={"prompt_id": "observation_count",
                          "query": "How many observations are open in Net Banking?",
                          "ram_profile": "worst_case_enterprise_dry_run"}).json()
    r = client.post("/api/audit-llm/validate-grounding", json={"result": q})
    assert r.status_code == 200
    assert r.json()["grounding"]["grounding"] in ("grounded", "weakly_grounded", "unsupported", "empty_answer")


def test_api_validate_grounding_explicit():
    r = client.post("/api/audit-llm/validate-grounding",
                    json={"answer": "unrelated claim about mars colonies", "evidence_context": {}})
    assert r.status_code == 200
    assert r.json()["grounding"]["grounding"] == "unsupported"


def test_workbench_has_eval_and_replay_buttons():
    r = client.get("/mvp/audit/llm-workbench?role=owner&user=UAT")
    assert r.status_code == 200
    assert "alw-btn-eval" in r.text and "alw-btn-replay" in r.text
