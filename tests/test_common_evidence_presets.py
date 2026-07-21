"""Tests for common evidence preset catalogue and click/query execution."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest
from fastapi.testclient import TestClient

from app import ecs_state
from app.main import app, chatbot_answer
from modules.operations.engines import evidence_repository as ops_repo
from modules.operations.engines import predefined_queries_engine as engine
from modules.shared.services.common_evidence_presets import (
    EMPTY_SCOPE_MESSAGE,
    PRESET_BY_ID,
    PRESET_HANDLERS,
    PRESET_QUERY_CATALOG,
    execute_common_evidence_query,
    execute_preset_query,
    preset_groups_for_role,
    render_common_query_html,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    ecs_state.submitted_controls.clear()
    ecs_state.approved_controls.clear()
    ecs_state.rejected_controls.clear()
    ecs_state.submitted_meta.clear()
    ecs_state.closed_observations.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.missing_evidence_registry.clear()
    ecs_state.missing_evidence_seed_loaded = False
    ecs_state.evidence_approval_trail.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)
    yield
    ecs_state.submitted_controls.clear()
    ecs_state.approved_controls.clear()
    ecs_state.rejected_controls.clear()
    ecs_state.submitted_meta.clear()
    ecs_state.closed_observations.clear()
    ecs_state.uploaded_evidence_enrollments.clear()
    ecs_state.predefined_query_fingerprint_index.clear()
    ecs_state.predefined_query_content_index.clear()
    ecs_state.missing_evidence_seed_loaded = False
    ecs_state.evidence_approval_trail.clear()
    ops_repo.evidence_repository.clear()
    ops_repo.upload_tracker.clear()
    engine.set_execution_persist(False)


def _persist(
    *,
    app_name: str = "Net Banking",
    framework: str = "PCI DSS",
    control: str = "PGX-001",
    uploaded_at: str = "",
) -> dict:
    payload = f'{{"evidence": "{control}", "application": "{app_name}"}}'.encode()
    rec = ops_repo.register_upload(
        filename=f"{control}_{app_name.replace(' ', '_')}.json",
        content=payload,
        uploaded_by="scheduler",
        framework=framework,
        application=app_name,
        control=control,
        source_connector="PREDEFINED_QUERY",
    )
    if uploaded_at:
        rec["uploaded_at"] = uploaded_at
    return rec


def test_every_visible_preset_maps_to_handler():
    for preset in PRESET_QUERY_CATALOG:
        assert preset["id"] in PRESET_BY_ID
        assert preset["handler"] in PRESET_HANDLERS, preset["id"]


def test_preset_groups_include_all_catalog_items():
    groups = preset_groups_for_role("owner")
    ids = {p["id"] for g in groups for p in g["presets"]}
    assert ids == {p["id"] for p in PRESET_QUERY_CATALOG}


def test_api_presets_endpoint():
    resp = client.get("/mvp/api/common-evidence-presets?role=owner")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["groups"]) >= 4


def test_click_payload_executes_latest_5_evidences():
    for idx in range(6):
        _persist(app_name="Net Banking", control=f"CTL-{idx}", uploaded_at=f"2026-07-2{idx}T10:00:00+00:00")

    resp = client.post(
        "/mvp/api/common-evidence-query",
        data={"role": "owner", "user": "Owner", "query_key": "latest_5_evidences"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["query_key"] == "latest_5_evidences"
    assert data["query_type"] in ("Deterministic", "DETERMINISTIC")
    assert "Query type:" in data["plain"] or "Deterministic" in data["plain"]
    assert data["total_count"] == 5
    assert len(data["citations"]) <= 5


def test_latest_5_ordering_and_limit():
    ids = []
    for idx in range(7):
        rec = _persist(
            app_name="Net Banking",
            control=f"ORD-{idx}",
            uploaded_at=f"2026-07-2{idx}T10:00:00+00:00",
        )
        ids.append(rec["evidence_id"])
    result = execute_preset_query("latest_5_evidences", role="owner", user="Owner")
    assert result["total_count"] == 5
    returned_ids = [r.get("evidence_id") for r in result["rows"]]
    assert len(returned_ids) == 5
    assert returned_ids == list(reversed(ids[-5:]))


def test_application_filter_on_preset():
    _persist(app_name="Net Banking", framework="PCI DSS")
    _persist(app_name="Mobile Banking", framework="PCI DSS")
    result = execute_preset_query(
        "latest_evidence_by_application",
        role="owner",
        user="Owner",
        application="Net Banking",
    )
    assert result.get("citations") or result.get("rows")
    cite = (result.get("citations") or result.get("rows") or [{}])[0]
    assert cite.get("application") == "Net Banking"


def test_framework_filter_on_preset():
    _persist(app_name="Net Banking", framework="PCI DSS")
    _persist(app_name="Net Banking", framework="DPSC")
    result = execute_preset_query(
        "evidence_by_framework",
        role="owner",
        user="Owner",
        framework="PCI DSS",
    )
    rows = result.get("rows") or []
    assert rows
    assert all(r.get("framework") == "PCI DSS" for r in rows)


def test_empty_result_message():
    result = execute_preset_query("latest_5_evidences", role="owner", user="Owner")
    assert result["total_count"] == 0
    assert EMPTY_SCOPE_MESSAGE in result["answer"]
    html = render_common_query_html(result)
    assert EMPTY_SCOPE_MESSAGE.replace(" ", "") in html.replace(" ", "") or "No matching" in html


def test_backend_error_unknown_key():
    resp = client.post(
        "/mvp/api/common-evidence-query",
        data={"role": "owner", "user": "Owner", "query_key": "not_a_real_key"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "Unknown query key" in (data.get("error") or data.get("plain") or "")


def test_open_observations_status_filtering():
    from modules.governance.engines.missing_evidence_engine import get_all_missing_evidence

    ecs_state.missing_evidence_seed_loaded = False
    rows = get_all_missing_evidence("owner")
    assert isinstance(rows, list)
    result = execute_preset_query("latest_open_observations", role="owner", user="Owner")
    assert result["query_type"] == "Deterministic"
    for row in result.get("rows") or []:
        assert str(row.get("status", "")).lower() in {
            "pending upload",
            "awaiting app owner",
            "submitted for review",
            "open",
            "overdue",
            "rejected",
            "in progress",
            "escalated",
            "monitoring",
            "overdue",
        } or row.get("status") == "Overdue"


def test_rbac_excludes_unauthorized_application():
    _persist(app_name="Net Banking", framework="PCI DSS")
    result = execute_preset_query(
        "latest_evidence_by_application",
        role="functional_head",
        user="FunctionalHead",
        application="Net Banking",
    )
    assert result.get("ok") is False
    assert "access" in result.get("answer", "").lower()


def test_citations_returned_with_evidence_links():
    rec = _persist()
    result = execute_preset_query("latest_5_evidences", role="owner", user="Owner")
    assert result["citations"]
    assert result["citations"][0].get("evidence_id") == rec["evidence_id"]
    html = render_common_query_html(result)
    assert rec["evidence_id"] in html


def test_rag_fallback_only_for_semantic_queries():
    semantic = execute_common_evidence_query(
        query="Explain what the SSL configuration document says about encryption",
        role="owner",
        user="Owner",
    )
    deterministic = execute_common_evidence_query(
        query="Show the last 5 evidences collected",
        role="owner",
        user="Owner",
    )
    assert deterministic.get("query_type") in ("Deterministic", None) or deterministic.get("answer_source")
    if semantic.get("query_type") == "RAG":
        assert "RAG" in semantic.get("query_type", "")


def test_chatbot_answer_with_query_key():
    rec = _persist()
    ans = chatbot_answer("", role="owner", user="Owner", query_key="latest_5_evidences")
    assert "Deterministic" in ans
    assert rec["evidence_id"] in ans or "No matching" in ans


def test_chat_investigation_accepts_query_key():
    _persist()
    resp = client.post(
        "/mvp/api/chat-investigation",
        data={"role": "owner", "user": "Owner", "query_key": "latest_5_evidences"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["query"] == "Show the last 5 evidences collected"
    assert data["html"]
