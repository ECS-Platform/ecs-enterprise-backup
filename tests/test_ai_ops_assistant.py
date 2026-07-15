"""ECS AI Ops Assistant — recovery and readiness tests."""

from __future__ import annotations

import os

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

from fastapi.testclient import TestClient

from modules.operations.engines.ai_ops_assistant_engine import SAMPLE_QUERY_GROUPS, SUMMARY_MODES, build_assistant_view
from app.main import app
from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS, try_operations_answer

client = TestClient(app, raise_server_exceptions=False)

Q = "?role=cio&user=cio@bank.com"


def test_ai_ops_assistant_page_loads():
    resp = client.get(f"/mvp/ai-ops-assistant{Q}")
    assert resp.status_code == 200, resp.text[:300]
    text = resp.text
    assert "ECS AI Ops Assistant" in text
    assert "ECS Operations Copilot" in text
    assert "Ask Copilot" in text
    assert "References &amp; Drilldowns" in text or "References & Drilldowns" in text


def test_nav_ai_ops_assistant_route_without_sidebar_link():
    """Page stays routable; the approved Phase-1 sidebar omits AI Ops Assistant."""
    assert client.get(f"/mvp/ai-ops-assistant{Q}").status_code == 200
    nav = client.get(f"/dashboard{Q}").text
    assert "AI Ops Assistant" not in nav
    assert "/mvp/ai-ops-assistant" not in nav


def test_sample_queries_present_on_page():
    resp = client.get(f"/mvp/ai-ops-assistant{Q}")
    assert resp.status_code == 200
    assert "Why is Net Banking down?" in resp.text
    assert "What is PCI DSS?" in resp.text
    assert "What is enterprise maturity?" in resp.text


def test_assistant_view_has_summary_modes():
    view = build_assistant_view("cio")
    assert len(view["summary_modes"]) == len(SUMMARY_MODES)
    assert view["incident_rows"]
    assert view.get("default_references")
    assert sum(len(g["queries"]) for g in view["sample_queries"]) >= 12


def test_outage_query_returns_structured_html():
    from modules.shared.services.chatbot_engine import get_chat_structured, clear_chat_structured

    clear_chat_structured("cio@bank.com", "cio")
    answer = try_operations_answer("Why is Net Banking down?", role="cio", user="cio@bank.com")
    assert answer is not None
    html = get_chat_structured("cio@bank.com", "cio")
    assert "Operations Intelligence" in html
    assert "Summary" in html


def test_all_summary_modes_generate_html():
    from modules.operations.engines.ai_ops_response_modes import render_all_mode_fingerprints
    from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS

    scenario = OUTAGE_SCENARIOS["net_banking"]
    fingerprints = render_all_mode_fingerprints(scenario, "net_banking", "cio", "cio@bank.com")
    assert len(fingerprints) == 8
    bodies = list(fingerprints.values())
    for i, html in enumerate(bodies):
        assert html, list(fingerprints.keys())[i]
    assert bodies[0] != bodies[1]
    assert "Customers Affected" in bodies[0] or "1.2M" in bodies[0]
    assert "API Latency" in bodies[1] or "Error Rate" in bodies[1]
    assert "Executive Attention" in bodies[2]
    assert "Controls Impacted" in bodies[3] or "Failed controls" in bodies[3].lower()
    assert "PCI DSS" in bodies[4]
    assert "Available" in bodies[5] and "Missing" in bodies[5]
    assert "Chronological timeline" in bodies[6] or "Primary Ticket" in bodies[6]
    assert "root cause" in bodies[7].lower()


def test_response_modes_are_distinct():
    from modules.operations.engines.ai_ops_response_modes import render_all_mode_fingerprints
    from modules.operations.engines.operations_intelligence import OUTAGE_SCENARIOS

    fps = render_all_mode_fingerprints(OUTAGE_SCENARIOS["net_banking"], "net_banking", "cio", "cio@bank.com")
    unique = set(fps.values())
    assert len(unique) == 8, "Each response mode must render unique HTML"


def test_chat_response_mode_api():
    resp = client.post(
        "/mvp/api/chat-response-mode",
        data={"scenario_key": "net_banking", "mode": "technical", "role": "cio", "user": "cio@bank.com"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["mode"] == "technical"
    assert "API Latency" in body["html"] or "Error Rate" in body["html"]
    assert "ecsOpsInvestigation" in body["shell_html"]


def test_outage_investigation_includes_mode_panel():
    from modules.shared.services.chatbot_engine import clear_chat_history, clear_chat_structured, get_chat_structured

    clear_chat_history("cio@bank.com", "cio")
    clear_chat_structured("cio@bank.com", "cio")
    try_operations_answer("Why is Net Banking down?", role="cio", user="cio@bank.com")
    html = get_chat_structured("cio@bank.com", "cio")
    assert "ecsChatModePanel" in html
    assert "ecsOpsInvestigation" in html
    assert "data-scenario-key=\"net_banking\"" in html
    assert "Business Summary" in html


def test_summary_mode_commands_via_engine():
    from modules.shared.services.chatbot_engine import clear_chat_structured, get_chat_structured

    for mode_id, _, _ in SUMMARY_MODES:
        clear_chat_structured("cio@bank.com", "cio")
        q = f"@outage-mode:net_banking:{mode_id}"
        ans = try_operations_answer(q, role="cio", user="cio@bank.com")
        assert ans is not None, mode_id
        html = get_chat_structured("cio@bank.com", "cio")
        assert html, mode_id


def test_banking_governance_queries_not_fallback():
    from app.main import chatbot_answer

    queries = [
        "What is PCI DSS?",
        "How many evidences are pending for me?",
        "Show high-risk controls",
        "Framework coverage",
    ]
    for q in queries:
        ans = chatbot_answer(q, role="cio", user="cio@bank.com")
        assert "I couldn't match" not in ans, q


def test_chat_post_returns_to_assistant_page():
    resp = client.post(
        "/mvp/chat",
        data={
            "query": "Why is Net Banking down?",
            "role": "cio",
            "user": "cio@bank.com",
            "return_url": "/mvp/ai-ops-assistant?role=cio&user=cio@bank.com",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/mvp/ai-ops-assistant" in resp.headers.get("location", "")
    assert "response=" in resp.headers.get("location", "")


def test_chat_action_api_drilldown():
    resp = client.post(
        "/mvp/api/chat-action",
        data={
            "action": "show_related_incidents",
            "role": "cio",
            "user": "cio@bank.com",
            "scenario": "net_banking",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("html")


def test_chat_investigation_clears_history():
    from modules.shared.services.chatbot_engine import clear_chat_history, clear_chat_structured, get_chat_history

    clear_chat_history("cio@bank.com", "cio")
    clear_chat_structured("cio@bank.com", "cio")
    r1 = client.post(
        "/mvp/api/chat-investigation",
        data={"query": "What is PCI DSS?", "role": "cio", "user": "cio@bank.com"},
    )
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["ok"] is True
    assert b1["query"] == "What is PCI DSS?"
    assert b1.get("html") or b1.get("plain")
    assert len(get_chat_history("cio@bank.com", "cio")) == 1

    r2 = client.post(
        "/mvp/api/chat-investigation",
        data={"query": "Show high-risk controls", "role": "cio", "user": "cio@bank.com"},
    )
    assert r2.status_code == 200
    history = get_chat_history("cio@bank.com", "cio")
    assert len(history) == 1
    assert history[0]["query"] == "Show high-risk controls"


def test_manual_chat_preserves_history():
    from modules.shared.services.chatbot_engine import clear_chat_history, clear_chat_structured, get_chat_history

    clear_chat_history("cio@bank.com", "cio")
    clear_chat_structured("cio@bank.com", "cio")
    for q in ("What is PCI DSS?", "Show high-risk controls"):
        resp = client.post(
            "/mvp/chat",
            data={
                "query": q,
                "role": "cio",
                "user": "cio@bank.com",
                "return_url": "/mvp/ai-ops-assistant?role=cio&user=cio@bank.com",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
    assert len(get_chat_history("cio@bank.com", "cio")) == 2


def test_investigation_ui_wiring():
    html = client.get(f"/mvp/ai-ops-assistant{Q}").text
    assert "Current Investigation" in html
    assert "startFreshInvestigation" in html
    assert "Loading investigation" in html
    assert 'id="ecsChatThread"' in html
