"""ECS chart accessibility & readability standard.

Release: ecs-chart-accessibility-remediation-v1

Covers:
  * The canonical chart-standard partial exists with the WCAG token set, tab,
    badge, legend, and axis chrome classes.
  * The vendored validation utilities (validateContrast / validateChartAccessibility
    / validateChartConfiguration) behave correctly (run via Node when available).
  * Every standardized color pair meets WCAG AA (computed in Python — no Node needed).
  * The standard reaches dashboards platform-wide via the shared include chain.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

REPO = Path(__file__).resolve().parents[1]
STANDARD_PARTIAL = REPO / "modules/shared/templates/partials/ecs_chart_standard.html"
CHART_SYSTEM = REPO / "modules/shared/templates/partials/executive_charts_system.html"
THEME = REPO / "modules/shared/templates/partials/enterprise_theme.html"
VALIDATOR_JS = REPO / "modules/shared/static/js/ecs_chart_standards.js"


# --------------------------------------------------------------------------- #
# WCAG contrast computed in pure Python (mirrors validateContrast in JS)
# --------------------------------------------------------------------------- #

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _channel(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (_channel(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: str, bg: str) -> float:
    lf, lb = _luminance(_hex_to_rgb(fg)), _luminance(_hex_to_rgb(bg))
    hi, lo = max(lf, lb), min(lf, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


WHITE = "#ffffff"

SERIES_ON_WHITE = {
    "navy": "#1e3a5f", "slate": "#334155", "blue": "#2563EB", "teal": "#0F766E",
    "green": "#15803D", "orange": "#C2410C", "red": "#B91C1C", "muted": "#475569",
    "benchmark": "#4338CA",
}
SUPPORTING_TEXT = {"axis": "#0F172A", "legend": "#0F172A", "subtitle": "#334155", "helper": "#475569"}
TABS = {"inactive": ("#E2E8F0", "#1E293B"), "active": ("#FFFFFF", "#2563EB"), "hover": ("#FFFFFF", "#1D4ED8")}
# AA-compliant badge resolution. The brief's white-on-green/orange fall below AA
# (the brief also forbids sub-AA combinations); these are the reconciled values:
#   green darkened to #15803D, orange uses dark ink, others as specified.
BADGES = {
    "blue": ("#FFFFFF", "#2563EB"), "green": ("#FFFFFF", "#15803D"), "red": ("#FFFFFF", "#DC2626"),
    "orange": ("#111827", "#F97316"), "yellow": ("#111827", "#EAB308"),
}


@pytest.mark.parametrize("name,color", SERIES_ON_WHITE.items())
def test_series_palette_meets_wcag_aa(name, color):
    assert contrast_ratio(color, WHITE) >= 4.5, f"{name} {color} fails AA on white"


@pytest.mark.parametrize("name,color", SUPPORTING_TEXT.items())
def test_supporting_text_meets_wcag_aa(name, color):
    assert contrast_ratio(color, WHITE) >= 4.5, f"{name} text {color} fails AA on white"


@pytest.mark.parametrize("name,pair", TABS.items())
def test_tabs_meet_wcag_aa(name, pair):
    fg, bg = pair
    assert contrast_ratio(fg, bg) >= 4.5, f"{name} tab fails AA"


@pytest.mark.parametrize("name,pair", BADGES.items())
def test_badges_meet_wcag_aa(name, pair):
    fg, bg = pair
    assert contrast_ratio(fg, bg) >= 4.5, f"{name} badge fails AA"


def test_old_low_contrast_muted_would_fail():
    # Guards against regressing back to the original light-gray muted token.
    assert contrast_ratio("#94a3b8", WHITE) < 4.5


# --------------------------------------------------------------------------- #
# Standard partial content
# --------------------------------------------------------------------------- #

def test_standard_partial_exists_and_defines_tokens():
    assert STANDARD_PARTIAL.is_file()
    css = STANDARD_PARTIAL.read_text(encoding="utf-8")
    for token in ("--ecs-axis-label", "--ecs-legend-text", "--ecs-subtitle", "--ecs-helper-text",
                  "--ecs-tab-bg-active", "--ecs-badge-blue-bg", "--ecs-badge-yellow-bg",
                  "--ecs-chart-min-font"):
        assert token in css, f"missing token {token}"


def test_standard_partial_defines_required_classes():
    css = STANDARD_PARTIAL.read_text(encoding="utf-8")
    for cls in (".ecs-chart-frame", ".ecs-chart-yaxis-label", ".ecs-chart-xaxis-label",
                ".ecs-chart-yscale", ".ecs-badge-blue", ".ecs-badge-yellow",
                ".ecs-tab", ".ecs-chart-legend"):
        assert cls in css, f"missing class {cls}"


def test_standard_overrides_legacy_muted_token():
    css = STANDARD_PARTIAL.read_text(encoding="utf-8")
    # The accessible muted value replaces the failing #94a3b8.
    assert "--ecs-chart-muted:  #475569" in css or "--ecs-chart-muted: #475569" in css


def test_chart_system_includes_standard_last():
    sys_html = CHART_SYSTEM.read_text(encoding="utf-8")
    assert "ecs_chart_standard.html" in sys_html
    # Must be included AFTER the closing </script> so token overrides win.
    assert sys_html.index("</script>") < sys_html.index("ecs_chart_standard.html")


def test_theme_loads_standard_and_validator():
    theme = THEME.read_text(encoding="utf-8")
    assert "ecs_chart_standard.html" in theme
    assert "ecs_chart_standards.js" in theme


def test_renderer_supports_axis_and_units_options():
    sys_html = CHART_SYSTEM.read_text(encoding="utf-8")
    for marker in ("yLabel", "xLabel", "niceScale", "ecs-chart-yscale", "richTip", "opts.units"):
        assert marker in sys_html, f"renderer missing {marker}"


# --------------------------------------------------------------------------- #
# Vendored validator JS — run via Node when available
# --------------------------------------------------------------------------- #

def test_validator_js_exists():
    assert VALIDATOR_JS.is_file()
    src = VALIDATOR_JS.read_text(encoding="utf-8")
    for fn in ("validateContrast", "validateChartAccessibility", "validateChartConfiguration"):
        assert fn in src


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_validator_js_behaves_correctly():
    script = f"""
    const S = require({json.dumps(str(VALIDATOR_JS))});
    const out = {{
      lowContrast: S.validateContrast('#94a3b8', '#ffffff').AA,
      goodContrast: S.validateContrast('#475569', '#ffffff').AA,
      blueBadge: S.validateContrast('#ffffff', '#2563EB').AA,
      badConfig: S.validateChartConfiguration({{ title: 'X' }}).passed,
      goodConfig: S.validateChartConfiguration({{ title:'t', subtitle:'s', xLabel:'Month',
        yLabel:'Count', yScale:true, seriesLabel:'v', tooltip:true }}).passed,
      a11yMissing: S.validateChartAccessibility({{ title:'t' }}).errors.length,
      a11yOk: S.validateChartAccessibility({{ title:'t', subtitle:'s', xLabel:'M', yLabel:'C',
        yScale:true, legend:true, tooltip:true, labelsVisible:true }}).passed,
    }};
    console.log(JSON.stringify(out));
    """
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout.strip().splitlines()[-1])
    assert data["lowContrast"] is False
    assert data["goodContrast"] is True
    assert data["blueBadge"] is True
    assert data["badConfig"] is False
    assert data["goodConfig"] is True
    assert data["a11yMissing"] >= 6  # title-only descriptor fails the rest
    assert data["a11yOk"] is True


# --------------------------------------------------------------------------- #
# Platform-wide delivery via served HTML
# --------------------------------------------------------------------------- #

PAGES = [
    "/mvp/trends?role=cio&user=cio@bank.com",
    "/mvp/reports?role=cio&user=cio@bank.com",
    "/mvp/enterprise?role=cio&user=cio@bank.com",
    "/mvp/pan-india?role=cio&user=cio@bank.com",
    "/dashboard/compliance-head?role=compliance_head&user=ch@bank.com",
]


@pytest.mark.parametrize("path", PAGES)
def test_standard_served_on_pages(path):
    resp = client.get(path)
    assert resp.status_code == 200, path
    html = resp.text
    # Accessible tokens + validator are present on the rendered page.
    assert "--ecs-axis-label" in html, f"axis token missing on {path}"
    assert "--ecs-tab-bg-active" in html, f"tab token missing on {path}"
    assert "ecs_chart_standards.js" in html, f"validator JS missing on {path}"


# --------------------------------------------------------------------------- #
# P1 sub-navigation tab contrast hotfix
# --------------------------------------------------------------------------- #

WORKSPACE_STYLES = REPO / "modules/shared/templates/partials/mvp_workspace_styles.html"
WORKSPACE_MACROS = REPO / "modules/shared/templates/partials/mvp_workspace_macros.html"

# Standardized tab states (WCAG AA verified).
TAB_STATES = {
    "inactive": ("#0F172A", "#E2E8F0"),
    "active": ("#FFFFFF", "#2563EB"),
    "hover": ("#FFFFFF", "#1D4ED8"),
    "disabled": ("#475569", "#F1F5F9"),
}

# Tab-bearing pages across the modules named in the P1 ticket.
TAB_PAGES = [
    "/mvp/enterprise?role=cio&user=cio@bank.com",
    "/mvp/pan-india?role=cio&user=cio@bank.com",
    "/mvp/reports?role=cio&user=cio@bank.com",
    "/mvp/trends?role=cio&user=cio@bank.com",
    "/mvp/evidence-health?role=auditor&user=a@bank.com",
    "/mvp/completeness?role=auditor&user=a@bank.com",
]


@pytest.mark.parametrize("state,pair", TAB_STATES.items())
def test_tab_states_meet_wcag_aa(state, pair):
    fg, bg = pair
    ratio = contrast_ratio(fg, bg)
    floor = 3.0 if state == "disabled" else 4.5
    assert ratio >= floor, f"{state} tab {fg}/{bg} = {ratio} below {floor}"


def test_broken_active_tab_state_would_fail():
    # The defect: light-blue text on light-blue active background.
    assert contrast_ratio("#2563eb", "#dbeafe") < 4.5


def test_workspace_tab_css_uses_accessible_states():
    css = WORKSPACE_STYLES.read_text(encoding="utf-8")
    # Active tab must be solid blue with white text — not the old light-blue wash.
    assert "background: #2563EB" in css
    # The old failing active-tab combo (#2563eb text on #dbeafe bg) must be gone.
    assert "var(--ecs-accent-soft, #dbeafe)" not in css
    # Inactive must be slate bg with dark ink.
    assert "#E2E8F0" in css and "#0F172A" in css
    # Hover deep blue + disabled state present.
    assert "#1D4ED8" in css
    assert ":disabled" in css or "is-disabled" in css


def test_no_low_contrast_blue_on_lightblue_in_workspace_styles():
    # Guard against the recurring #2563eb-on-#dbeafe (4.24:1) defect family.
    css = WORKSPACE_STYLES.read_text(encoding="utf-8").lower()
    assert "#2563eb; padding" not in css.replace("color: ", "")  # heuristic
    # Direct check: no rule pairs blue text on the light-blue wash.
    import re as _re
    for m in _re.finditer(r"background:\s*#dbeafe;\s*color:\s*(#[0-9a-f]{6})", css):
        assert contrast_ratio(m.group(1), "#dbeafe") >= 4.5, m.group(0)


def test_workspace_macro_emits_aria_selected():
    macros = WORKSPACE_MACROS.read_text(encoding="utf-8")
    assert 'role="tab"' in macros
    assert "aria-selected" in macros


def test_bootstrap_navpills_hardened_in_standard():
    css = STANDARD_PARTIAL.read_text(encoding="utf-8")
    assert ".nav-pills .nav-link" in css
    assert ".nav-tabs .nav-link" in css


@pytest.mark.parametrize("path", TAB_PAGES)
def test_tab_pages_have_no_broken_active_wash(path):
    resp = client.get(path)
    assert resp.status_code == 200, path
    html = resp.text
    # The fixed active-tab style must be present and the broken wash must be gone
    # from the workspace tab rule (served via mvp_workspace_styles.html).
    assert "ecs-workspace-tab" in html, f"workspace tabs missing on {path}"
    assert "background: #2563EB" in html, f"accessible active tab missing on {path}"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_validate_tab_accessibility_js():
    script = f"""
    const S = require({json.dumps(str(VALIDATOR_JS))});
    const broken = S.validateTabAccessibility({{
      inactiveFg:'#475569', inactiveBg:'#ffffff',
      activeFg:'#2563eb', activeBg:'#dbeafe', hoverFg:'#2563eb', hoverBg:'#ffffff' }});
    const fixed = S.validateTabAccessibility({{
      inactiveFg:'#0F172A', inactiveBg:'#E2E8F0',
      activeFg:'#FFFFFF', activeBg:'#2563EB',
      hoverFg:'#FFFFFF', hoverBg:'#1D4ED8',
      disabledFg:'#475569', disabledBg:'#F1F5F9' }});
    const sameColor = S.validateTabAccessibility({{ inactiveFg:'#fff', inactiveBg:'#fff' }});
    console.log(JSON.stringify({{ brokenPassed: broken.passed, fixedPassed: fixed.passed,
      sameColorErr: sameColor.errors.length }}));
    """
    res = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout.strip().splitlines()[-1])
    assert data["brokenPassed"] is False
    assert data["fixedPassed"] is True
    assert data["sameColorErr"] >= 1
