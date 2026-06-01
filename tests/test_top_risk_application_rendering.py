"""Regression tests — Top Risk Applications table must not wrap one character per line."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)
Q = "?role=cio&user=cio@bank.com"
ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "top_risk_applications_verification.html"

DEMO_APP_NAMES = [
    "Customer Onboarding Platform",
    "Mobile Banking Edge",
    "Enterprise Payments Hub",
    "Digital Lending Platform",
    "Core Banking Platform",
]


def _fetch_demo_overview() -> str:
    resp = client.get(f"/mvp/demo-overview{Q}")
    assert resp.status_code == 200
    return resp.text


def test_top_risk_table_excluded_from_executive_table_crush():
    """Global ecs-executive-table JS must not enhance demo top-risk table."""
    html = _fetch_demo_overview()
    assert "ecs-skip-exec-table" in html
    assert "ecs-top-risk-applications" in html
    assert "data-ecs-top-risk-table" in html
    assert "if (table.classList.contains('demo-table')" in html
    assert "ecsProtectTopRiskTable" in html
    assert "<colgroup>" in html
    assert 'class="col-app" style="min-width:250px;width:250px"' in html


def test_top_risk_column_width_and_word_break_css():
    html = _fetch_demo_overview()
    assert re.search(r"\.col-app\s*\{[^}]*min-width:\s*250px\s*!important", html)
    assert re.search(r"word-break:\s*normal\s*!important", html)
    assert "word-break: break-all" not in html.split("ecs-top-risk-applications")[1].split("</style>")[0]
    assert re.search(r"\.col-risk\s*\{[^}]*min-width:\s*80px", html)
    assert re.search(r"\.col-readiness\s*\{[^}]*min-width:\s*100px", html)
    assert re.search(r"\.col-owner\s*\{[^}]*min-width:\s*150px", html)


def test_top_risk_horizontal_scroll_container():
    html = _fetch_demo_overview()
    assert "demo-table-wrap" in html
    assert re.search(r"overflow-x:\s*auto", html)
    assert re.search(r"min-width:\s*580px", html)


def test_top_risk_demo_application_names_present():
    html = _fetch_demo_overview()
    for name in DEMO_APP_NAMES:
        assert name in html, f"Missing demo app: {name}"


def test_top_risk_application_cells_are_readable():
    """Application names appear as full strings inside col-app cells, not split per character."""
    html = _fetch_demo_overview()
    table_match = re.search(
        r'<table[^>]*data-ecs-top-risk-table[^>]*>.*?</table>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    assert table_match, "Top risk table not found"
    table_html = table_match.group(0)
    app_cells = re.findall(r'<td class="col-app"><strong>([^<]+)</strong></td>', table_html)
    for name in DEMO_APP_NAMES:
        assert name in app_cells, f"Application cell not readable for: {name}"
    for cell in app_cells[:5]:
        assert len(cell.strip()) > 3
        assert "\n" not in cell
        assert not re.fullmatch(r"(.)\1*", cell.replace(" ", ""))


def test_top_risk_app_column_width_exceeds_200px():
    html = _fetch_demo_overview()
    m = re.search(r"min-width:\s*(\d+)px\s*!important", html)
    assert m and int(m.group(1)) > 200


def test_top_risk_rendered_html_artifact():
    """Save rendered HTML for manual / screenshot verification."""
    html = _fetch_demo_overview()
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(html, encoding="utf-8")
    assert ARTIFACT.exists() and ARTIFACT.stat().st_size > 5000
    table_match = re.search(
        r'<table[^>]*data-ecs-top-risk-table[^>]*>.*?</table>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    assert table_match
    snippet = table_match.group(0)
    assert "Customer Onboarding Platform" in snippet
    assert 'class="col-app"' in snippet
    assert "<colgroup>" in snippet
    assert "word-break: normal !important" in html
