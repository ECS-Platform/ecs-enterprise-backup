"""ECS AI Ops Assistant — recovery and readiness tests."""

from __future__ import annotations

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


def test_nav_contains_ai_ops_assistant():
    resp = client.get(f"/mvp/demo-overview{Q}")
    assert resp.status_code == 200
    assert "AI Ops Assistant" in resp.text
    assert "/mvp/ai-ops-assistant" in resp.text


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
    from modules.operations.engines.ai_ops_assistant_engine import build_summary_mode_html

    scenario = OUTAGE_SCENARIOS["net_banking"]
    for mode_id, label, _btn in SUMMARY_MODES:
        html = build_summary_mode_html(scenario, mode_id, "net_banking", "cio", "cio@bank.com")
        assert label.split()[0] in html or mode_id.replace("_", " ").title() in html
        assert "Drilldown" in html or "href=" in html


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
