#!/usr/bin/env python3
"""Phase-1 hybrid chatbot retrieval-quality baseline harness (evaluation only).

Reuses the same service entry points as ``app.main.chatbot_answer``:
  * ``@ceq:`` / query_key → ``common_evidence_presets.execute_preset_query``
  * deterministic intents → ``try_deterministic_evidence_query``
  * evidence-catalog free text → ``try_rag_evidence_query``
  * no-evidence / refusal messages from those paths

Does **not** call ``ecs_platform.rag.answer`` alone (that would skip preset/deterministic).
Does **not** modify production retrieval, ranking, authoritative reader, or RAG.

Usage (from repo root):

    python scripts/run_phase1_chatbot_retrieval_benchmark.py \\
        --config benchmarks/config/phase1_chatbot_retrieval_config.json

Structure check only (no 60-question execution):

    python scripts/run_phase1_chatbot_retrieval_benchmark.py \\
        --config benchmarks/config/phase1_chatbot_retrieval_config.json \\
        --validate-only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Demo-safe defaults before importing the app stack.
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Host-side defaults mirrored from scripts/benchmark_env.sh (Compose publish ports).
_HOST_BENCHMARK_DEFAULTS = {
    "ECS_REPO_PG_HOST": "localhost",
    "ECS_REPO_PG_PORT": "5433",
    "ECS_REPO_PG_DATABASE": "ecs_repository",
    "ECS_REPO_PG_USER": "ecs_user",
    "ECS_REPO_PG_PASSWORD": "ecs_password",
    "ECS_VECTOR_PG_HOST": "localhost",
    "ECS_VECTOR_PG_PORT": "5434",
    "ECS_VECTOR_PG_PASSWORD": "ecs_password",
    "ECS_LLM_PROVIDER": "ollama",
    "OLLAMA_URL": "http://localhost:11434",
    "OLLAMA_MODEL": "qwen3:8b",
    "ECS_EMBEDDING_MODEL": "nomic-embed-text",
    "PYTHONPATH": ".",
}

EVIDENCE_ID_RE = re.compile(r"\bEVD-\d{5}\b", re.I)
REFUSAL_MARKERS = (
    "no supporting evidence was found in ecs",
    "no matching evidence was found for the selected scope",
    "no rejected evidences in the current workflow state",
    "no evidence found in ecs repository.",
    "access denied",
    "you do not have access to evidence",
)

# Eval-only control-id aliases (framework_catalog PCI-C## ↔ control titles).
_CONTROL_ID_EQUIVALENCE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset(
        {
            "pci-c01",
            "req 3.4 — encryption at rest",
            "req 3.4 - encryption at rest",
            "req 3.4 encryption at rest",
        }
    ),
)

# Presets that return gap/summary/observation listings without EVD citations by design.
_NON_EVD_LISTING_PRESET_IDS = frozenset(
    {
        "control_without_evidence",
        "failed_evidence_collection",
        "application_collection_summary",
        "framework_collection_summary",
        "observations_by_application",
        "observations_by_framework",
    }
)


def _apply_host_side_benchmark_endpoints() -> dict[str, str]:
    """Eval-only: reuse host endpoint convention from ``scripts/benchmark_env.sh``.

    Loads ``.env`` via ``app.env_bootstrap`` (override=False), then rewrites
    Compose DNS / ``host.docker.internal`` values that are unreachable from a
    Windows/macOS host Python process. Does not change production code paths.
    """
    applied: dict[str, str] = {}

    # Import for side-effect load of repo-root .env (may set OLLAMA_URL to
    # host.docker.internal — rewritten below for host-side execution).
    try:
        from app import env_bootstrap as _env_bootstrap  # noqa: F401
    except Exception:  # noqa: BLE001
        pass

    for key, value in _HOST_BENCHMARK_DEFAULTS.items():
        if key not in os.environ or not str(os.environ.get(key, "")).strip():
            os.environ[key] = value
            applied[key] = value

    ollama = str(os.environ.get("OLLAMA_URL", "")).strip().rstrip("/")
    if "host.docker.internal" in ollama.lower():
        os.environ["OLLAMA_URL"] = "http://localhost:11434"
        applied["OLLAMA_URL"] = os.environ["OLLAMA_URL"]

    repo_host = str(os.environ.get("ECS_REPO_PG_HOST", "")).strip().lower()
    if repo_host in {"postgres", "postgres-demo"}:
        os.environ["ECS_REPO_PG_HOST"] = "localhost"
        applied["ECS_REPO_PG_HOST"] = "localhost"
        # Container listens on 5432; Compose publishes repository on host 5433.
        if str(os.environ.get("ECS_REPO_PG_PORT", "")).strip() in {"", "5432"}:
            os.environ["ECS_REPO_PG_PORT"] = "5433"
            applied["ECS_REPO_PG_PORT"] = "5433"

    vector_host = str(os.environ.get("ECS_VECTOR_PG_HOST", "")).strip().lower()
    if vector_host == "pgvector":
        os.environ["ECS_VECTOR_PG_HOST"] = "localhost"
        applied["ECS_VECTOR_PG_HOST"] = "localhost"
        if str(os.environ.get("ECS_VECTOR_PG_PORT", "")).strip() in {"", "5432"}:
            os.environ["ECS_VECTOR_PG_PORT"] = "5434"
            applied["ECS_VECTOR_PG_PORT"] = "5434"

    # Host .env often keeps container-default port 5432 + placeholder password.
    if str(os.environ.get("ECS_REPO_PG_HOST", "")).strip().lower() in {"localhost", "127.0.0.1"}:
        if str(os.environ.get("ECS_REPO_PG_PORT", "")).strip() == "5432":
            os.environ["ECS_REPO_PG_PORT"] = "5433"
            applied["ECS_REPO_PG_PORT"] = "5433"
        if str(os.environ.get("ECS_REPO_PG_PASSWORD", "")).strip() in {"", "change-me"}:
            os.environ["ECS_REPO_PG_PASSWORD"] = "ecs_password"
            applied["ECS_REPO_PG_PASSWORD"] = "ecs_password"

    if str(os.environ.get("ECS_VECTOR_PG_HOST", "")).strip().lower() in {"localhost", "127.0.0.1"}:
        if str(os.environ.get("ECS_VECTOR_PG_PORT", "")).strip() in {"", "5432"}:
            os.environ["ECS_VECTOR_PG_PORT"] = "5434"
            applied["ECS_VECTOR_PG_PORT"] = "5434"

    return applied


def _preflight_ollama(timeout_sec: float = 5.0) -> dict[str, Any]:
    """Fail fast if the effective Ollama base URL is unreachable."""
    import urllib.error
    import urllib.request

    base = str(os.environ.get("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            return {
                "ok": True,
                "ollama_url": base,
                "http_status": getattr(resp, "status", 200),
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "ollama_url": base,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=True, indent=2)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _norm_control_token(value: Any) -> str:
    return (
        _norm(value)
        .replace("—", "-")
        .replace("–", "-")
        .replace("  ", " ")
    )


def _control_alias_set(value: Any) -> set[str]:
    """Expand a control id/title into its eval-only equivalence set."""
    token = _norm_control_token(value)
    if not token:
        return set()
    out = {token, _norm(value)}
    for group in _CONTROL_ID_EQUIVALENCE_GROUPS:
        normalized_group = {_norm_control_token(x) for x in group} | {_norm(x) for x in group}
        if token in normalized_group or _norm(value) in normalized_group:
            out |= normalized_group
    return {t for t in out if t}


def _controls_equivalent(expected: Any, actual: Any) -> bool:
    exp = _control_alias_set(expected)
    act = _control_alias_set(actual)
    if not exp or not act:
        return False
    if exp & act:
        return True
    # Retain substring tolerance used by generic field matching.
    for e in exp:
        for a in act:
            if e in a or a in e:
                return True
    return False


def _is_refusal_text(answer: str) -> bool:
    text = _norm(answer)
    return any(marker in text for marker in REFUSAL_MARKERS)


def _parse_citations_from_formatted(answer_text: str) -> list[dict[str, Any]]:
    """Best-effort parse of formatted chatbot citation lines (fallback only)."""
    citations: list[dict[str, Any]] = []
    if "Citations:" not in (answer_text or ""):
        return citations
    block = answer_text.split("Citations:", 1)[1]
    for line in block.splitlines():
        line = line.strip().lstrip("- ").strip()
        if not line or "|" not in line:
            continue
        parts = [p.strip() for p in line.split("|")]
        evidence_token = parts[0].split()[0] if parts[0] else ""
        citations.append(
            {
                "evidence_id": evidence_token,
                "control_id": parts[1] if len(parts) > 1 else "",
                "application": parts[2] if len(parts) > 2 else "",
                "source_connector": parts[3] if len(parts) > 3 else "",
                "object_key": parts[4] if len(parts) > 4 else "",
                "framework": "",
            }
        )
    return citations


def _persist_citation_metadata(citations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact citation records for offline diagnosis (eval output only)."""
    out: list[dict[str, Any]] = []
    for cite in citations:
        out.append(
            {
                "evidence_id": cite.get("evidence_id") or "",
                "application": cite.get("application") or "",
                "framework": cite.get("framework") or "",
                "control": cite.get("control_id") or cite.get("control") or "",
                "source_connector": cite.get("source_connector") or "",
            }
        )
    return out


def observe_hybrid_chatbot(
    question: str,
    *,
    role: str,
    user: str,
    application: str = "",
    framework: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    """Mirror ``chatbot_answer`` routing; return structured observation (eval-only).

    Stops after the first selected hybrid channel (preset → deterministic → RAG).
    Does **not** invoke RAG after a successful deterministic/preset hit.

    Indexing side-effects from authoritative hydration (``store_evidence`` →
    ``index_after_persist`` → embed) are suppressed for preset/deterministic
    reads via ``suppress_startup_indexing`` — same mechanism as app startup.
    RAG query-time embedding/generation remains enabled on the RAG branch only.
    """
    from ecs_platform.evidence_indexing import suppress_startup_indexing
    from app import ecs_state
    from modules.shared.services.common_evidence_presets import execute_preset_query
    from modules.shared.services.common_evidence_queries import (
        format_evidence_chat_response,
        is_evidence_catalog_query,
        try_deterministic_evidence_query,
        try_rag_evidence_query,
    )

    timings: dict[str, Any] = {
        "preset_ms": 0,
        "deterministic_ms": 0,
        "rag_ms": 0,
        "format_ms": 0,
        "index_after_persist_ms": 0,
        "index_after_persist_calls": 0,
        "embed_ms": 0,
        "embed_calls": 0,
        "llm_generate_ms": 0,
        "llm_generate_calls": 0,
        "paths_attempted": [],
    }

    with _stage_probes(timings):
        query = question or ""
        q = query.lower()
        fw_hint = ""
        for name in ecs_state.frameworks:
            if name.lower() in q:
                fw_hint = name
                break
        if framework:
            fw_hint = framework

        query_key = ""
        if query.startswith("@ceq:"):
            query_key = query.split(":", 1)[1].strip()
            query = ""

        if query_key:
            timings["paths_attempted"].append("preset")
            # Hydration during preset handlers must not trigger live embedding.
            with suppress_startup_indexing():
                t0 = time.perf_counter()
                result = execute_preset_query(
                    query_key,
                    role=role,
                    user=user,
                    application=application,
                    framework=framework,
                    run_id=run_id,
                )
                timings["preset_ms"] = int((time.perf_counter() - t0) * 1000)
            t1 = time.perf_counter()
            formatted = format_evidence_chat_response(result, fw_hint)
            timings["format_ms"] = int((time.perf_counter() - t1) * 1000)
            return {
                "actual_retrieval_path": "preset",
                "answer_source": result.get("answer_source") or result.get("query_type") or "Deterministic",
                "intent": result.get("intent") or "",
                "query_key": query_key,
                "answer": result.get("answer") or "",
                "formatted_answer": formatted,
                "citations": list(result.get("citations") or []),
                "rows": list(result.get("rows") or []),
                "applied_filters": dict(result.get("applied_filters") or {}),
                "rag_mode": "",
                "ok": bool(result.get("ok", True)),
                "channel": "preset",
                "stage_timings": timings,
            }

        timings["paths_attempted"].append("deterministic")
        # Deterministic handlers call collect_persisted_evidence_rows →
        # authoritative reader → ai_repo.search → hydrate → store_evidence →
        # index_after_persist. Suppress indexing so eval does not embed ~N rows
        # per question; do not call RAG after a deterministic hit.
        with suppress_startup_indexing():
            t0 = time.perf_counter()
            det = try_deterministic_evidence_query(query, role=role, user=user)
            timings["deterministic_ms"] = int((time.perf_counter() - t0) * 1000)
        if det is not None:
            t1 = time.perf_counter()
            formatted = format_evidence_chat_response(det, fw_hint)
            timings["format_ms"] = int((time.perf_counter() - t1) * 1000)
            return {
                "actual_retrieval_path": "deterministic",
                "answer_source": det.get("answer_source") or "DETERMINISTIC",
                "intent": det.get("intent") or "",
                "query_key": "",
                "answer": det.get("answer") or "",
                "formatted_answer": formatted,
                "citations": list(det.get("citations") or []),
                "rows": [],
                "rag_mode": "",
                "ok": True,
                "channel": "deterministic",
                "stage_timings": timings,
            }

        if is_evidence_catalog_query(query):
            timings["paths_attempted"].append("rag")
            # RAG branch: query embedding + optional LLM generation stay enabled.
            t0 = time.perf_counter()
            rag = try_rag_evidence_query(query, role=role, user=user, framework=fw_hint)
            timings["rag_ms"] = int((time.perf_counter() - t0) * 1000)
            if rag is not None:
                t1 = time.perf_counter()
                formatted = format_evidence_chat_response(rag, fw_hint)
                timings["format_ms"] = int((time.perf_counter() - t1) * 1000)
                return {
                    "actual_retrieval_path": "rag",
                    "answer_source": rag.get("answer_source") or "RAG",
                    "intent": rag.get("intent") or "free_text",
                    "query_key": "",
                    "answer": rag.get("answer") or "",
                    "formatted_answer": formatted,
                    "citations": list(rag.get("citations") or []),
                    "rows": [],
                    "rag_mode": str(rag.get("rag_mode") or ""),
                    "ok": True,
                    "channel": "rag",
                    "stage_timings": timings,
                }

    return {
        "actual_retrieval_path": "fallback",
        "answer_source": "FALLBACK",
        "intent": "",
        "query_key": "",
        "answer": "",
        "formatted_answer": "",
        "citations": [],
        "rows": [],
        "rag_mode": "",
        "ok": False,
        "channel": "fallback",
        "note": "Query did not enter preset/deterministic/RAG hybrid channels",
        "stage_timings": timings,
    }



@contextmanager
def _stage_probes(timings: dict[str, Any]):
    """Eval-only probes around indexing / embed / generate (no production changes)."""
    from ecs_platform import evidence_indexing as ei
    from ecs_platform.llm_engine.provider import LLMProvider

    orig_index = ei.index_after_persist
    orig_post = LLMProvider._post_json

    def _wrapped_index(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        out = orig_index(*args, **kwargs)
        timings["index_after_persist_ms"] = int(
            timings.get("index_after_persist_ms", 0) + (time.perf_counter() - t0) * 1000
        )
        timings["index_after_persist_calls"] = int(timings.get("index_after_persist_calls", 0)) + 1
        if ei._startup_indexing_suppressed():  # noqa: SLF001 - eval probe
            timings["index_suppressed_calls"] = int(timings.get("index_suppressed_calls", 0)) + 1
        return out

    def _wrapped_post(self: Any, url: str, payload: dict[str, Any], headers: dict[str, str]) -> Any:
        t0 = time.perf_counter()
        out = orig_post(self, url, payload, headers)
        dt_ms = int((time.perf_counter() - t0) * 1000)
        u = str(url or "").lower()
        if "embedding" in u or "embedcontent" in u or u.endswith("/embeddings"):
            timings["embed_ms"] = int(timings.get("embed_ms", 0) + dt_ms)
            timings["embed_calls"] = int(timings.get("embed_calls", 0)) + 1
        elif (
            "/api/chat" in u
            or "generatecontent" in u
            or "/chat/completions" in u
            or "/v1/messages" in u
        ):
            timings["llm_generate_ms"] = int(timings.get("llm_generate_ms", 0) + dt_ms)
            timings["llm_generate_calls"] = int(timings.get("llm_generate_calls", 0)) + 1
        else:
            timings["provider_http_other_ms"] = int(timings.get("provider_http_other_ms", 0) + dt_ms)
        return out

    ei.index_after_persist = _wrapped_index  # type: ignore[assignment]
    LLMProvider._post_json = _wrapped_post  # type: ignore[assignment]
    try:
        yield
    finally:
        ei.index_after_persist = orig_index  # type: ignore[assignment]
        LLMProvider._post_json = orig_post  # type: ignore[assignment]


def _repo_evidence_snapshot() -> list[dict[str, Any]]:
    """Read-only scoring snapshot with one-time canonical hydrate (no indexing)."""
    from ecs_platform.evidence_indexing import suppress_startup_indexing
    from modules.shared.services.common_evidence_queries import collect_persisted_evidence_rows

    try:
        with suppress_startup_indexing():
            try:
                from modules.audit_intelligence.engines import evidence_repository as ai_repo

                n = ai_repo.hydrate_from_canonical_repository(force=True)
                print(f"[benchmark] canonical hydrate (indexing suppressed) rows_merged={n}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[benchmark] canonical hydrate skipped: {type(exc).__name__}: {exc}",
                    flush=True,
                )
            return collect_persisted_evidence_rows()
    except Exception as exc:  # noqa: BLE001
        print(f"[benchmark] evidence snapshot unavailable: {type(exc).__name__}: {exc}", flush=True)
        return []


def _supporting_rows_exist(
    item: dict[str, Any],
    rows: list[dict[str, Any]],
    observation: dict[str, Any] | None = None,
) -> bool:
    """Return whether the source used by the expected intent produced scoped data."""
    state_dependent_intents = {
        "approved_evidence",
        "rejected_evidence",
        "pending_auditor",
        "pending_app_owner",
        "duplicate_attempts",
        "missing_evidence",
        "date_range",
        "control_approved",
    }
    expected_intent = str(item.get("expected_deterministic_intent") or "")
    if expected_intent in state_dependent_intents:
        observed = observation or {}
        if (
            observed.get("actual_retrieval_path") != "deterministic"
            or observed.get("intent") != expected_intent
        ):
            return False
        answer = str(observed.get("answer") or observed.get("formatted_answer") or "")
        # These handlers already query their authoritative workflow/queue/gap/date
        # source. Their scoped refusal is stronger evidence of absence than the
        # presence of an ordinary application/framework evidence row.
        return bool(answer.strip()) and not _is_refusal_text(answer)

    if not rows:
        return False
    exp_app = item.get("expected_application")
    exp_fw = item.get("expected_framework")
    exp_ctrl = item.get("expected_control_or_query")
    exp_src = item.get("expected_source_connector")
    if not any([exp_app, exp_fw, exp_ctrl, exp_src]):
        return bool(rows)

    for row in rows:
        app = row.get("application") or ""
        fw = row.get("framework") or ""
        ctrl = str(row.get("control_id") or row.get("control") or "")
        src = str(row.get("source_connector") or row.get("source_type") or "")
        if exp_app and _norm(app) != _norm(exp_app):
            continue
        if exp_fw and _norm(fw) != _norm(exp_fw):
            continue
        if exp_ctrl and not _controls_equivalent(exp_ctrl, ctrl):
            continue
        if exp_src and _norm(exp_src) not in _norm(src) and _norm(src) != _norm(exp_src):
            continue
        return True
    return False


def _citation_field_match(citations: list[dict[str, Any]], field: str, expected: str | None) -> str:
    if not expected:
        return "n/a"
    if not citations:
        return "missing"
    values = [_norm(c.get(field)) for c in citations]
    exp = _norm(expected)
    if field == "control_id":
        raw_values = [c.get(field) for c in citations]
        if any(_controls_equivalent(expected, v) for v in raw_values if v):
            return "match"
        return "mismatch"
    if any(exp == v or exp in v or v in exp for v in values if v):
        return "match"
    return "mismatch"


def _score_citations(
    item: dict[str, Any],
    citations: list[dict[str, Any]],
    *,
    expect_refusal: bool,
    repo_ids: set[str],
) -> str:
    if expect_refusal:
        return "n/a" if not citations else "weak"
    if not citations:
        return "missing"

    shape_ok = 0
    grounded = 0
    for cite in citations:
        eid = str(cite.get("evidence_id") or "")
        if EVIDENCE_ID_RE.search(eid) or eid:
            shape_ok += 1
        if eid and eid.upper() in repo_ids:
            grounded += 1
        elif eid and eid.upper() in {r.upper() for r in repo_ids}:
            grounded += 1

    meta_hits = []
    for field, key in (
        ("application", "expected_application"),
        ("framework", "expected_framework"),
        ("control_id", "expected_control_or_query"),
        ("source_connector", "expected_source_connector"),
    ):
        expected = item.get(key)
        if expected:
            meta_hits.append(_citation_field_match(citations, field, expected))

    if meta_hits and any(h == "mismatch" for h in meta_hits):
        return "weak"
    if shape_ok and (grounded or not repo_ids):
        # If repo empty, shape-only is weak (cannot prove grounding).
        return "valid" if grounded else "weak"
    if shape_ok:
        return "weak"
    return "missing"


def _score_hallucination(
    *,
    expect_refusal: bool,
    answer: str,
    citations: list[dict[str, Any]],
    repo_ids: set[str],
    data_available: bool,
) -> str:
    refused = _is_refusal_text(answer)
    cited_ids = [str(c.get("evidence_id") or "") for c in citations if c.get("evidence_id")]
    if repo_ids:
        invented = [
            eid
            for eid in cited_ids
            if eid.upper().startswith("EVD-") and eid.upper() not in repo_ids
        ]
        grounded_evd = [
            eid
            for eid in cited_ids
            if eid.upper().startswith("EVD-") and eid.upper() in repo_ids
        ]
    else:
        # Empty corpus cannot prove invention except known negative probes.
        invented = [eid for eid in cited_ids if eid.upper() == "EVD-99999"]
        grounded_evd = []
    # Mixed citation sets: unknown EVD siblings are ignored when at least one
    # cited EVD is verifiably present in the authoritative snapshot.
    all_evd_unknown = bool(invented) and not grounded_evd
    # Also flag known negative-probe ids if presented as real hits with detail beyond refusal.
    if any(eid.upper() == "EVD-99999" for eid in cited_ids) and not refused:
        return "unsupported"

    if expect_refusal:
        if refused and not invented and not cited_ids:
            return "correct_refusal"
        if refused and not all_evd_unknown:
            return "correct_refusal"
        if all_evd_unknown or (cited_ids and not refused):
            return "unsupported"
        if not refused and answer.strip():
            return "unsupported"
        return "correct_refusal"

    if all_evd_unknown:
        return "unsupported"
    if refused and data_available:
        return "incorrect_refusal"
    if refused and not data_available:
        return "correct_refusal"
    if cited_ids and (not repo_ids or any(eid.upper() in repo_ids for eid in cited_ids)):
        return "grounded"
    if cited_ids and repo_ids and not any(eid.upper() in repo_ids for eid in cited_ids):
        return "unsupported"
    if answer.strip() and not refused:
        # Text without citations is not counted as grounded.
        return "unsupported"
    return "incorrect_refusal" if data_available else "correct_refusal"


def _path_outcome(
    expected_path: str,
    actual_path: str,
    *,
    expect_refusal: bool,
    hallucination: str,
) -> tuple[bool, str]:
    """Return (path_aligned, note). Does not reclassify RAG as deterministic."""
    if expected_path == "no_evidence":
        aligned = hallucination == "correct_refusal" or (
            actual_path in {"deterministic", "preset", "rag", "no_evidence", "fallback"}
            and hallucination == "correct_refusal"
        )
        return aligned, "refusal_behavior"
    if expected_path == actual_path:
        return True, "exact_channel"
    return False, f"expected_{expected_path}_got_{actual_path}"


def _non_evd_listing_preset_key(item: dict[str, Any], observation: dict[str, Any]) -> str:
    if (item.get("expected_retrieval_path") or "") != "preset":
        return ""
    key = str(observation.get("query_key") or item.get("expected_preset_id") or "").strip()
    if key in _NON_EVD_LISTING_PRESET_IDS:
        return key
    return ""


def _non_evd_listing_preset_ok(
    item: dict[str, Any],
    observation: dict[str, Any],
    *,
    answer: str,
) -> bool:
    """True when a known non-EVD listing preset returned a usable structured result."""
    key = _non_evd_listing_preset_key(item, observation)
    if not key:
        return False
    expected = item.get("expected_preset_id")
    if expected and observation.get("query_key") != expected:
        return False
    if (observation.get("actual_retrieval_path") or "") != "preset":
        return False
    if _is_refusal_text(answer):
        return False
    rows = list(observation.get("rows") or [])
    text = (answer or "").strip()
    return bool(text) and (bool(rows) or "result:" in _norm(text) or "missing evidence" in _norm(text))


def _deterministic_missing_evidence_ok(
    item: dict[str, Any],
    observation: dict[str, Any],
    *,
    answer: str,
) -> bool:
    """Recognize the deterministic structured gap contract, which has no EVD cites."""
    if item.get("expected_retrieval_path") != "deterministic":
        return False
    if observation.get("actual_retrieval_path") != "deterministic":
        return False
    if observation.get("intent") != "missing_evidence":
        return False
    if item.get("expected_deterministic_intent") not in (None, "missing_evidence"):
        return False
    text = (answer or "").strip()
    return (
        bool(text)
        and not _is_refusal_text(text)
        and "missing evidence gaps:" in _norm(text)
        and "\n" in text
    )


def _observation_scope_field_match(
    observation: dict[str, Any],
    field: str,
    expected: str | None,
) -> str:
    """Match app/framework for observation presets via filters/rows/answer (eval-only)."""
    if not expected:
        return "n/a"
    exp = _norm(expected)
    filters = observation.get("applied_filters") or {}
    filter_val = filters.get(field)
    if filter_val and (_norm(filter_val) == exp or exp in _norm(filter_val) or _norm(filter_val) in exp):
        return "match"
    for row in observation.get("rows") or []:
        val = row.get(field)
        if val and (_norm(val) == exp or exp in _norm(val) or _norm(val) in exp):
            return "match"
    answer = _norm(observation.get("answer") or "")
    if exp and exp in answer:
        return "match"
    return "missing"


def score_question(
    item: dict[str, Any],
    observation: dict[str, Any],
    *,
    rows: list[dict[str, Any]],
    skip_unreliable: bool,
) -> dict[str, Any]:
    expected_path = item.get("expected_retrieval_path") or ""
    actual_path = observation.get("actual_retrieval_path") or "fallback"
    expect_refusal = bool(item.get("expect_no_evidence_or_refusal"))
    reliability = item.get("validation_reliability") or "conditional"

    citations = list(observation.get("citations") or [])
    if not citations and observation.get("formatted_answer"):
        citations = _parse_citations_from_formatted(str(observation["formatted_answer"]))

    answer = str(observation.get("answer") or observation.get("formatted_answer") or "")
    repo_ids = {str(r.get("evidence_id") or "").upper() for r in rows if r.get("evidence_id")}
    data_available = _supporting_rows_exist(item, rows, observation)
    non_evd_listing_ok = _non_evd_listing_preset_ok(item, observation, answer=answer)
    deterministic_gap_ok = _deterministic_missing_evidence_ok(
        item, observation, answer=answer
    )

    # Unavailable: unreliable skipped, or positive-path needs data that is not present.
    unavailable = False
    unavailable_reason = ""
    if skip_unreliable and reliability == "unreliable":
        unavailable = True
        unavailable_reason = "validation_reliability=unreliable"
    elif (
        not expect_refusal
        and expected_path in {"deterministic", "preset", "rag"}
        and reliability in {"conditional", "unreliable"}
        and not data_available
        and _is_refusal_text(answer)
        and not non_evd_listing_ok
        and not deterministic_gap_ok
    ):
        unavailable = True
        unavailable_reason = "required_evidence_not_seeded"

    citation_result = _score_citations(
        item, citations, expect_refusal=expect_refusal, repo_ids=repo_ids
    )
    if (non_evd_listing_ok or deterministic_gap_ok) and not citations:
        citation_result = "n/a"

    hallucination = _score_hallucination(
        expect_refusal=expect_refusal,
        answer=answer,
        citations=citations,
        repo_ids=repo_ids,
        data_available=data_available,
    )
    # Non-EVD listing presets: non-empty structured answers are grounded without EVD cites.
    if (
        (non_evd_listing_ok or deterministic_gap_ok)
        and hallucination == "unsupported"
        and not citations
    ):
        hallucination = "grounded"

    path_aligned, path_note = _path_outcome(
        expected_path,
        actual_path,
        expect_refusal=expect_refusal,
        hallucination=hallucination,
    )

    metadata_match = {
        "application": _citation_field_match(
            citations, "application", item.get("expected_application")
        ),
        "framework": _citation_field_match(
            citations, "framework", item.get("expected_framework")
        ),
        "control_or_query": _citation_field_match(
            citations, "control_id", item.get("expected_control_or_query")
        ),
        "source_connector": _citation_field_match(
            citations, "source_connector", item.get("expected_source_connector")
        ),
    }
    # Observation listing presets: scope comes from applied filters / OBS rows, not EVD cites.
    obs_key = _non_evd_listing_preset_key(item, observation)
    if obs_key in {"observations_by_application", "observations_by_framework"}:
        if item.get("expected_application"):
            metadata_match["application"] = _observation_scope_field_match(
                observation, "application", item.get("expected_application")
            )
        if item.get("expected_framework"):
            metadata_match["framework"] = _observation_scope_field_match(
                observation, "framework", item.get("expected_framework")
            )

    # Score expected_preset_id only for preset-path catalogue items.
    if expected_path == "preset" and item.get("expected_preset_id"):
        if observation.get("query_key") == item.get("expected_preset_id"):
            metadata_match["preset_id"] = "match"
        else:
            metadata_match["preset_id"] = "mismatch" if observation.get("query_key") else "missing"
    else:
        metadata_match["preset_id"] = "n/a"

    if item.get("expected_deterministic_intent"):
        if _norm(observation.get("intent")) == _norm(item.get("expected_deterministic_intent")):
            metadata_match["deterministic_intent"] = "match"
        elif actual_path == "deterministic":
            metadata_match["deterministic_intent"] = "mismatch"
        else:
            metadata_match["deterministic_intent"] = "missing"
    else:
        metadata_match["deterministic_intent"] = "n/a"

    if unavailable:
        retrieval_result = "unavailable"
    elif expect_refusal:
        retrieval_result = "correct" if hallucination == "correct_refusal" else "wrong"
    elif not path_aligned:
        # Never reclassify an unexpected channel (e.g. RAG→deterministic) as success.
        retrieval_result = "wrong"
    elif (
        (non_evd_listing_ok or deterministic_gap_ok)
        and path_aligned
        and hallucination == "grounded"
    ):
        scope_ok = True
        if obs_key == "observations_by_application" and item.get("expected_application"):
            scope_ok = metadata_match.get("application") == "match"
        elif obs_key == "observations_by_framework" and item.get("expected_framework"):
            scope_ok = metadata_match.get("framework") == "match"
        retrieval_result = "correct" if scope_ok else "wrong"
    elif hallucination == "unsupported":
        retrieval_result = "wrong"
    elif hallucination == "incorrect_refusal":
        retrieval_result = "missing"
    elif not citations:
        # Text-only answers are not correct for positive evidence questions.
        if data_available:
            retrieval_result = "missing"
        else:
            retrieval_result = "unavailable"
            unavailable = True
            unavailable_reason = unavailable_reason or "no_citations_and_no_seeded_evidence"
    elif citation_result == "valid" and hallucination == "grounded":
        retrieval_result = "correct"
    elif citation_result == "weak":
        retrieval_result = "wrong"
    elif citation_result == "missing":
        retrieval_result = "missing"
    else:
        retrieval_result = "wrong"

    return {
        "question_id": item.get("id"),
        "question": item.get("question"),
        "categories": item.get("categories") or [],
        "validation_reliability": reliability,
        "expected_retrieval_path": expected_path,
        "actual_retrieval_path": actual_path,
        "path_aligned": path_aligned,
        "path_note": path_note,
        "expected_metadata_match": metadata_match,
        "retrieval_result": retrieval_result,
        "citation_result": citation_result,
        "hallucination_result": hallucination,
        "expect_no_evidence_or_refusal": expect_refusal,
        "data_available_for_filters": data_available,
        "unavailable": unavailable,
        "unavailable_reason": unavailable_reason,
        "latency_ms": observation.get("latency_ms"),
        "answer_source": observation.get("answer_source"),
        "intent": observation.get("intent"),
        "query_key": observation.get("query_key"),
        "rag_mode": observation.get("rag_mode"),
        "citation_count": len(citations),
        "citations": _persist_citation_metadata(citations),
        "answer_preview": (answer or "")[:280],
        "error": observation.get("error"),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    executed = [r for r in results if r.get("retrieval_result") != "unavailable" and not r.get("error_fatal")]
    scored = [r for r in results if r.get("retrieval_result") in {"correct", "wrong", "missing"}]
    unavailable = [r for r in results if r.get("retrieval_result") == "unavailable"]

    correct = sum(1 for r in scored if r["retrieval_result"] == "correct")
    wrong = sum(1 for r in scored if r["retrieval_result"] == "wrong")
    missing = sum(1 for r in scored if r["retrieval_result"] == "missing")

    cite_scored = [r for r in scored if r.get("citation_result") in {"valid", "weak", "missing"}]
    cite_valid = sum(1 for r in cite_scored if r["citation_result"] == "valid")

    unsupported = sum(1 for r in scored if r.get("hallucination_result") == "unsupported")
    refusal_items = [r for r in scored if r.get("expect_no_evidence_or_refusal")]
    correct_refusals = sum(1 for r in refusal_items if r.get("hallucination_result") == "correct_refusal")

    by_category: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    by_path: dict[str, dict[str, int]] = defaultdict(lambda: Counter())
    for r in results:
        bucket = r.get("retrieval_result") or "unknown"
        for cat in r.get("categories") or ["uncategorized"]:
            by_category[cat][bucket] += 1
        by_path[str(r.get("expected_retrieval_path") or "unknown")][bucket] += 1

    latencies = [int(r["latency_ms"]) for r in results if isinstance(r.get("latency_ms"), int)]
    denom = len(scored) or 1
    return {
        "total_questions": len(results),
        "executed_questions": len(executed),
        "scored_questions": len(scored),
        "unavailable_unverifiable": len(unavailable),
        "retrieval_accuracy": round(100.0 * correct / denom, 2) if scored else None,
        "correct_retrieval_count": correct,
        "wrong_retrieval_count": wrong,
        "missing_retrieval_count": missing,
        "citation_validity_rate": round(100.0 * cite_valid / (len(cite_scored) or 1), 2) if cite_scored else None,
        "hallucination_unsupported_answer_count": unsupported,
        "correct_refusal_rate": round(100.0 * correct_refusals / (len(refusal_items) or 1), 2)
        if refusal_items
        else None,
        "results_by_category": {k: dict(v) for k, v in sorted(by_category.items())},
        "results_by_expected_retrieval_path": {k: dict(v) for k, v in sorted(by_path.items())},
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
        },
    }


def validate_runner_structure(config: dict[str, Any], catalogue: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    questions = catalogue.get("questions") or []
    if len(questions) < 50:
        errors.append(f"catalogue has {len(questions)} questions; need >= 50")
    if not config.get("catalogue_path"):
        errors.append("config missing catalogue_path")
    required = set(catalogue.get("required_category_coverage") or [])
    seen = {c for q in questions for c in (q.get("categories") or [])}
    missing = required - seen
    if missing:
        errors.append(f"missing required categories: {sorted(missing)}")
    # Import graph for hybrid path (structure only).
    try:
        from modules.shared.services import common_evidence_presets  # noqa: F401
        from modules.shared.services import common_evidence_queries  # noqa: F401
        from modules.shared.services import evidence_authoritative_reader  # noqa: F401
    except Exception as exc:  # pragma: no cover
        errors.append(f"import failure: {exc}")
    return errors


def run_benchmark(
    config: dict[str, Any],
    catalogue: dict[str, Any],
    *,
    limit: int | None = None,
    path: str | None = None,
    ids: set[str] | None = None,
) -> dict[str, Any]:
    role = str(config.get("role") or "owner")
    user = str(config.get("user") or "phase1-retrieval-validator")
    skip_unreliable = bool((config.get("scoring") or {}).get("skip_unreliable_by_default", True))
    questions = list(catalogue.get("questions") or [])
    if path:
        questions = [
            q for q in questions if (q.get("expected_retrieval_path") or "") == path
        ]
    if ids:
        questions = [q for q in questions if str(q.get("id") or "") in ids]
    if limit is not None and limit > 0:
        questions = questions[:limit]
    total = len(questions)

    print(
        f"[benchmark] OLLAMA_URL={os.environ.get('OLLAMA_URL')} "
        f"ECS_REPO_PG={os.environ.get('ECS_REPO_PG_HOST')}:{os.environ.get('ECS_REPO_PG_PORT')} "
        f"ECS_VECTOR_PG={os.environ.get('ECS_VECTOR_PG_HOST')}:{os.environ.get('ECS_VECTOR_PG_PORT')}",
        flush=True,
    )
    print("[benchmark] collecting read-only evidence snapshot (indexing suppressed)…", flush=True)
    rows = _repo_evidence_snapshot()
    print(f"[benchmark] snapshot rows={len(rows)}", flush=True)

    results: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc).isoformat()

    for idx, item in enumerate(questions, start=1):
        qid = item.get("id") or f"q-{idx}"
        print(f"[{idx}/{total}] {qid} …", flush=True)
        q_start = time.perf_counter()
        try:
            obs = observe_hybrid_chatbot(
                str(item.get("question") or ""),
                role=role,
                user=user,
            )
            obs["latency_ms"] = int((time.perf_counter() - q_start) * 1000)
            scored = score_question(item, obs, rows=rows, skip_unreliable=skip_unreliable)
            scored["stage_timings"] = obs.get("stage_timings") or {}
            st = scored["stage_timings"]
            print(
                f"[{idx}/{total}] {qid} "
                f"path={scored.get('actual_retrieval_path')} "
                f"result={scored.get('retrieval_result')} "
                f"latency_ms={scored.get('latency_ms')} "
                f"stages={{det={st.get('deterministic_ms', 0)}, "
                f"preset={st.get('preset_ms', 0)}, "
                f"rag={st.get('rag_ms', 0)}, "
                f"embed={st.get('embed_ms', 0)}/{st.get('embed_calls', 0)}, "
                f"llm={st.get('llm_generate_ms', 0)}/{st.get('llm_generate_calls', 0)}, "
                f"index={st.get('index_after_persist_ms', 0)}/{st.get('index_after_persist_calls', 0)}, "
                f"attempted={st.get('paths_attempted')}}}",
                flush=True,
            )
        except Exception as exc:
            scored = {
                "question_id": item.get("id"),
                "question": item.get("question"),
                "categories": item.get("categories") or [],
                "expected_retrieval_path": item.get("expected_retrieval_path"),
                "actual_retrieval_path": "error",
                "retrieval_result": "unavailable",
                "citation_result": "missing",
                "hallucination_result": "unsupported",
                "unavailable": True,
                "unavailable_reason": f"infrastructure_error:{type(exc).__name__}",
                "error": str(exc),
                "error_fatal": False,
                "latency_ms": int((time.perf_counter() - q_start) * 1000),
                "traceback": traceback.format_exc(limit=3),
                "stage_timings": {},
            }
            print(
                f"[{idx}/{total}] {qid} INFRA ERROR: {type(exc).__name__}: {exc}",
                flush=True,
            )
        results.append(scored)

    finished = datetime.now(timezone.utc).isoformat()
    summary = aggregate(results)
    summary.update(
        {
            "benchmark_id": config.get("benchmark_id"),
            "started_at": started,
            "finished_at": finished,
            "role": role,
            "user": user,
            "skip_unreliable_by_default": skip_unreliable,
            "persisted_evidence_rows_at_start": len(rows),
            "catalogue_id": catalogue.get("catalogue_id"),
            "catalogue_version": catalogue.get("version"),
            "question_limit": limit,
            "path_filter": path,
            "id_filter": sorted(ids) if ids else None,
            "effective_ollama_url": os.environ.get("OLLAMA_URL"),
            "effective_repo_pg": (
                f"{os.environ.get('ECS_REPO_PG_HOST')}:{os.environ.get('ECS_REPO_PG_PORT')}"
            ),
            "effective_vector_pg": (
                f"{os.environ.get('ECS_VECTOR_PG_HOST')}:{os.environ.get('ECS_VECTOR_PG_PORT')}"
            ),
        }
    )
    return {"summary": summary, "results": results}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Phase-1 hybrid chatbot retrieval-quality baseline benchmark."
    )
    parser.add_argument(
        "--config",
        default="benchmarks/config/phase1_chatbot_retrieval_config.json",
        help="Path to phase1 chatbot retrieval config JSON.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate runner/config/catalogue structure without executing the 60 questions.",
    )
    parser.add_argument(
        "--include-unreliable",
        action="store_true",
        help="Score unreliable catalogue items instead of marking them unavailable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Execute only the first N catalogue questions (0 = all).",
    )
    parser.add_argument(
        "--path",
        choices=("deterministic", "preset", "rag", "no_evidence", "fallback"),
        default=None,
        help="Filter catalogue by expected_retrieval_path before applying --limit.",
    )
    parser.add_argument(
        "--ids",
        default="",
        help="Comma-separated catalogue question ids to run (e.g. P1-RQ-037,P1-RQ-054).",
    )
    args = parser.parse_args()

    endpoint_applied = _apply_host_side_benchmark_endpoints()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    config = _load_json(config_path)

    catalogue_path = Path(config["catalogue_path"])
    if not catalogue_path.is_absolute():
        catalogue_path = ROOT / catalogue_path
    catalogue = _load_json(catalogue_path)

    if args.include_unreliable:
        config.setdefault("scoring", {})["skip_unreliable_by_default"] = False

    struct_errors = validate_runner_structure(config, catalogue)
    if struct_errors:
        print("STRUCTURE VALIDATION FAILED:")
        for err in struct_errors:
            print(f"  - {err}")
        return 2

    if args.validate_only:
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "validate-only",
                    "questions": len(catalogue.get("questions") or []),
                    "catalogue_path": str(catalogue_path),
                    "entry_point": config.get("entry_point"),
                    "hybrid_channels": ["preset", "deterministic", "rag", "no_evidence"],
                    "structure_errors": [],
                    "effective_ollama_url": os.environ.get("OLLAMA_URL"),
                    "host_endpoints_applied": endpoint_applied,
                    "supports_limit": True,
                },
                indent=2,
            )
        )
        return 0

    preflight = _preflight_ollama()
    if not preflight.get("ok"):
        print("INFRASTRUCTURE PREFLIGHT FAILED (Ollama unreachable)", flush=True)
        print(f"  effective OLLAMA_URL={preflight.get('ollama_url')}", flush=True)
        print(f"  error={preflight.get('error')}", flush=True)
        print(
            "  Fix: ensure Ollama is listening on localhost:11434, or export "
            "OLLAMA_URL=http://localhost:11434 (not host.docker.internal).",
            flush=True,
        )
        return 3

    print(
        f"[benchmark] Ollama preflight ok url={preflight.get('ollama_url')}",
        flush=True,
    )

    output_dir = Path(config.get("output_dir") or "benchmarks/output/phase1_chatbot_retrieval")
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    os.environ["ECS_BENCHMARK_DIR"] = str(output_dir)

    limit = int(args.limit) if int(args.limit or 0) > 0 else None
    id_filter = {part.strip() for part in str(args.ids or "").split(",") if part.strip()} or None
    payload = run_benchmark(config, catalogue, limit=limit, path=args.path, ids=id_filter)
    _write_json(output_dir / "phase1_chatbot_retrieval_summary.json", payload["summary"])
    _write_json(output_dir / "phase1_chatbot_retrieval_results.json", payload["results"])

    summary = payload["summary"]
    print("Phase-1 chatbot retrieval baseline complete")
    print(f"  total={summary['total_questions']} executed={summary['executed_questions']} "
          f"scored={summary['scored_questions']} unavailable={summary['unavailable_unverifiable']}")
    print(f"  retrieval_accuracy={summary['retrieval_accuracy']}% "
          f"correct={summary['correct_retrieval_count']} wrong={summary['wrong_retrieval_count']} "
          f"missing={summary['missing_retrieval_count']}")
    print(f"  citation_validity_rate={summary['citation_validity_rate']}% "
          f"unsupported={summary['hallucination_unsupported_answer_count']} "
          f"correct_refusal_rate={summary['correct_refusal_rate']}%")
    print(f"  output={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
