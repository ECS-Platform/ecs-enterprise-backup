"""LLM/RAG validation readiness — pytest for the RAG answer() path (Scope 3).

These are the GENUINE coverage gap: the audit LLM workbench (classify, token
estimate, dry-run, fallback, 16/20 GB profile rules, "exactly three profiles")
is already covered by tests/test_audit_llm_workbench.py — NOT duplicated here.

This file covers the previously-untested ``ecs_platform.rag.answer`` pipeline,
fully offline (retrieval/provider/RBAC are monkeypatched — no DB, no live model):
  * RAG grounded answer with mocked evidence context + citation/source fields,
  * deterministic no-LLM fallback (provider not configured),
  * refusal / limitation handling when there is no evidence (grounding gate),
  * RBAC-safe response (denied role never reaches retrieval or the model),
and adds an explicit guard that NO 28 GB / 60 GB profile appears anywhere in the
benchmark config or the LLM workbench UI.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

from ecs_platform import rag

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Helpers: a fake evidence record (matches _enrich() output shape) + provider.
# --------------------------------------------------------------------------- #
def _fake_evidence(uid="EV-1"):
    return {
        "evidence_uid": uid, "source_system": "jira", "object_type": "ticket",
        "application": "Net Banking", "collected_timestamp": "2026-01-01T00:00:00Z",
        "frameworks": ["PCI-DSS"], "framework_refs": ["PCI-DSS 10.2"],
        "review_status": "approved", "controls": ["LOG-1"],
        "url": "https://jira/EV-1", "title": "Audit log ticket",
    }


class _FakeProvider:
    def __init__(self, configured=True, model="test-model"):
        self._configured = configured
        self.model = model

    def configured(self):
        return self._configured

    def generate_with_metadata(self, prompt, system=""):
        return ("Grounded answer citing [E1].",
                {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15})


def _patch_pipeline(monkeypatch, *, allowed=True, evidence=None, provider=None,
                    facts=None, mode="repository"):
    monkeypatch.setattr(rag, "_rbac_filter", lambda role, user: {
        "allowed": allowed, "reason": "" if allowed else "role not permitted",
        "scope_filter": {}, "rbac_role": role})
    ev = evidence if evidence is not None else []
    uids = [e["evidence_uid"] for e in ev]
    monkeypatch.setattr(rag, "_retrieve", lambda q, sf, h, k: (uids, mode, len(uids)))
    monkeypatch.setattr(rag, "_enrich", lambda u: ev)
    monkeypatch.setattr(rag, "_governance_facts", lambda q: facts or [])
    monkeypatch.setattr(rag, "_parse_hints", lambda q: {
        "application": None, "framework": None, "status": None, "source_system": None})
    monkeypatch.setattr(rag, "_persist_metric", lambda m: None)
    # _assemble_prompt is an internal formatting step (not under test here); stub it
    # so the orchestration/branching + citation assembly can be asserted offline.
    monkeypatch.setattr(rag, "_assemble_prompt", lambda q, f, e: "PROMPT")
    if provider is not None:
        import ecs_platform.llm_engine.provider as prov
        monkeypatch.setattr(prov, "get_provider", lambda: provider)


# --------------------------------------------------------------------------- #
# 1. RAG grounded answer (mocked evidence + provider) — citations/source fields
# --------------------------------------------------------------------------- #
def test_rag_answer_grounded_with_evidence(monkeypatch):
    _patch_pipeline(monkeypatch, allowed=True, evidence=[_fake_evidence()],
                    provider=_FakeProvider(configured=True))
    out = rag.answer("Show PCI logging evidence", role="cio", user="U")
    assert out["ok"] is True
    assert out["grounded"] is True
    assert out["mode"] == "rag"
    assert out["answer"]
    # Citation/source-reference fields are present and well-formed.
    assert out["citations"], "expected citations"
    c0 = out["citations"][0]
    assert c0["ref"] == "E1"
    assert c0["evidence_uid"] == "EV-1"
    assert c0["source_system"] == "jira"
    assert "PCI-DSS" in c0["frameworks"]
    assert out.get("request_id")


# --------------------------------------------------------------------------- #
# 2. Deterministic no-LLM fallback (provider not configured)
# --------------------------------------------------------------------------- #
def test_rag_answer_fallback_when_provider_unconfigured(monkeypatch):
    _patch_pipeline(monkeypatch, allowed=True, evidence=[_fake_evidence()],
                    provider=_FakeProvider(configured=False))
    out = rag.answer("Show PCI logging evidence", role="cio", user="U")
    assert out["ok"] is True
    assert out["grounded"] is False
    assert out["mode"] == "fallback"
    # Fallback still returns the structured retrieval (citations), just no LLM text.
    assert out["citations"]


# --------------------------------------------------------------------------- #
# 3. Refusal / limitation handling (grounding gate: no evidence, no facts)
# --------------------------------------------------------------------------- #
def test_rag_answer_refuses_without_evidence(monkeypatch):
    _patch_pipeline(monkeypatch, allowed=True, evidence=[],
                    provider=_FakeProvider(configured=True), facts=[])
    out = rag.answer("Anything with no evidence", role="cio", user="U")
    assert out["ok"] is True
    assert out["grounded"] is False
    assert out["mode"] == "no_evidence"
    assert out["answer"] == rag.NO_EVIDENCE_MESSAGE
    assert out["citations"] == []


def test_no_evidence_message_is_a_refusal():
    # The refusal message must not fabricate an answer.
    assert rag.NO_EVIDENCE_MESSAGE
    assert "no" in rag.NO_EVIDENCE_MESSAGE.lower() or "not" in rag.NO_EVIDENCE_MESSAGE.lower()


# --------------------------------------------------------------------------- #
# 4. RBAC-safe response (denied never reaches retrieval/model)
# --------------------------------------------------------------------------- #
def test_rag_answer_rbac_denied(monkeypatch):
    called = {"retrieve": False}

    def _boom_retrieve(*a, **k):
        called["retrieve"] = True
        return ([], "repository", 0)

    monkeypatch.setattr(rag, "_rbac_filter", lambda role, user: {
        "allowed": False, "reason": "role not permitted", "scope_filter": {},
        "rbac_role": role})
    monkeypatch.setattr(rag, "_retrieve", _boom_retrieve)
    monkeypatch.setattr(rag, "_persist_metric", lambda m: None)

    out = rag.answer("secret", role="nobody", user="U")
    assert out["ok"] is False
    assert out["mode"] == "denied"
    assert out["grounded"] is False
    assert "denied" in out["answer"].lower()
    assert out["citations"] == []
    assert called["retrieve"] is False  # short-circuited before retrieval


# --------------------------------------------------------------------------- #
# 5. Governance-facts-only grounding (evidence empty but facts apply -> not refused)
# --------------------------------------------------------------------------- #
def test_rag_answer_grounded_on_facts_only(monkeypatch):
    _patch_pipeline(monkeypatch, allowed=True, evidence=[],
                    provider=_FakeProvider(configured=True),
                    facts=[{"fact": "Enterprise compliance is 86%"}])
    out = rag.answer("What is enterprise compliance", role="cio", user="U")
    # With facts present the grounding gate passes -> LLM path (mode rag), not refused.
    assert out["mode"] == "rag"
    assert out["ok"] is True


# --------------------------------------------------------------------------- #
# 6. No 28 GB / 60 GB profile anywhere in benchmark config or workbench UI
# --------------------------------------------------------------------------- #
def test_no_28gb_or_60gb_profile_in_config():
    # A 28/60 GB machine must not appear as a PROFILE. The file's header comment
    # legitimately states "there is no 28 GB machine", so assert on structure
    # (profile ids + ram_gb values) rather than raw substrings.
    import re
    import yaml

    cfg_path = ROOT / "config" / "audit_llm_benchmark_profiles.yaml"
    data = yaml.safe_load(cfg_path.read_text())
    profiles = data.get("profiles", {})
    assert set(profiles) == {"local_16gb_safe", "local_20gb_extended",
                             "worst_case_enterprise_dry_run"}
    rams = {int(p.get("ram_gb", 0)) for p in profiles.values()}
    assert rams.issubset({0, 16, 20}), f"unexpected ram_gb values: {rams}"
    # No profile id may reference 28/60.
    assert not any("28" in k or "60" in k for k in profiles)


def test_no_28gb_or_60gb_profile_in_workbench_ui():
    ui = (ROOT / "modules" / "audit_intelligence" / "templates" / "audit"
          / "llm_workbench.html").read_text().lower()
    assert "28gb" not in ui and "28 gb" not in ui
    assert "60gb" not in ui and "60 gb" not in ui


def test_only_three_ram_profiles_exist():
    from modules.audit_intelligence.llm import prompt_library
    ids = {p["id"] for p in prompt_library.list_profiles()}
    assert ids == {"local_16gb_safe", "local_20gb_extended", "worst_case_enterprise_dry_run"}


# --------------------------------------------------------------------------- #
# 7. rag_status / llm_connectivity never raise offline (readiness signals)
# --------------------------------------------------------------------------- #
def test_rag_status_offline_safe():
    st = rag.rag_status()
    assert isinstance(st, dict)


def test_llm_connectivity_offline_safe():
    conn = rag.llm_connectivity()
    assert isinstance(conn, dict)
