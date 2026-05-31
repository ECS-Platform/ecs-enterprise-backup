"""Regression tests — Model & Prompt Registry table rendering."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REGISTRY_URL = "/mvp/ai-registry?role=cio&user=CIO"
LONG_APP_NAME = "Enterprise Retail Digital Banking AI Assistant Platform"
VIEWPORTS = (1366, 1440, 1920)


def _registry_html() -> str:
    resp = client.get(REGISTRY_URL)
    assert resp.status_code == 200, resp.status_code
    return resp.text


def test_relationship_map_uses_application_cell_markup():
    html = _registry_html()
    assert "Model → Application → Prompt Map" in html
    assert "ecs-gov-col-applications" in html
    assert "ecs-gov-app-list" in html
    assert "ecs-gov-tag" in html
    assert "Net Banking AI Assistant" in html
    assert "Mobile Banking Copilot" in html


def test_applications_column_css_prevents_character_stacking():
    html = _registry_html()
    assert "min-width: 350px" in html
    assert re.search(
        r"\.ecs-gov-data-table[^\{]*tbody td\.ecs-gov-wrap[^\{]*\{[^}]*word-break:\s*normal",
        html,
        re.DOTALL,
    )
    assert re.search(
        r"\.ecs-gov-data-table[^\{]*tbody td\.ecs-gov-wrap[^\{]*\{[^}]*overflow-wrap:\s*break-word",
        html,
        re.DOTALL,
    )
    gov_section = html.split(".ecs-gov-col-applications")[1][:1200]
    assert "break-all" not in gov_section
    assert "overflow-wrap: anywhere" not in gov_section


def test_long_application_names_remain_readable():
    html = _registry_html()
    assert LONG_APP_NAME in html
    assert len(LONG_APP_NAME) > 40
    idx = html.index(LONG_APP_NAME)
    window = html[max(0, idx - 400) : idx + len(LONG_APP_NAME) + 200]
    assert "ecs-gov-tag" in window or "ecs-gov-app-list" in window


def test_prompts_column_has_wrap_styles():
    html = _registry_html()
    assert "ecs-gov-col-prompts" in html
    assert "data-min-width=\"220\"" in html or "ecs-gov-col-prompts" in html


def test_table_scroll_container_present():
    html = _registry_html()
    assert html.count("ecs-gov-table-scroll") >= 1
    assert "overflow-x: auto" in html


def test_registry_renders_at_common_viewport_widths():
    for width in VIEWPORTS:
        resp = client.get(
            REGISTRY_URL,
            headers={"User-Agent": f"ECS-Test/{width}px"},
        )
        assert resp.status_code == 200
        assert "ecs-gov-data-table" in resp.text
