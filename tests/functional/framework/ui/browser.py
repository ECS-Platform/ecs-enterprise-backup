"""Reusable Playwright UI helper: login/logout, navigation, forms, dropdowns, upload, tables, search, filters,
dashboard widgets, drill-down, modals, notifications, download/export, role-based visibility.

Playwright is imported lazily so the API/DB/storage parts of the framework work without it installed.
ECS has no session login: ``/login`` redirects to a role dashboard carrying ``?role=&user=`` and these query params ARE
the identity in demo mode, so ``login_as`` drives the real login form and then keeps the resulting URL parameters.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

from ..config import FunctionalConfig
from ..errors import CapabilityBlocked
from . import selectors as S


class UiSession:
    def __init__(self, cfg: FunctionalConfig, artifacts_dir: Path | None = None) -> None:
        self.cfg = cfg
        self.artifacts_dir = artifacts_dir
        self._pw: Any = None
        self._browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self.identity: dict[str, str] = {}

    # ---- lifecycle ---------------------------------------------------------------------------------------------
    def start(self) -> "UiSession":
        if not self.cfg.get("ui.enabled"):
            raise CapabilityBlocked("UI automation disabled (set ECS_FT_UI_ENABLED=true and install Playwright).", requires="ui.enabled")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CapabilityBlocked("Playwright not installed (pip install playwright && playwright install chromium).",
                                    requires="playwright") from exc
        ui = self.cfg.get("ui", {})
        self._pw = sync_playwright().start()
        self._browser = getattr(self._pw, ui.get("browser", "chromium")).launch(
            headless=bool(ui.get("headless", True)), slow_mo=int(ui.get("slow_mo_ms", 0)))
        self.context = self._browser.new_context(base_url=self.cfg.ui_url, accept_downloads=True,
                                                 ignore_https_errors=not bool(self.cfg.get("verify_tls", True)))
        self.context.set_default_timeout(self.cfg.timeout * 1000)
        self.page = self.context.new_page()
        return self

    def stop(self) -> None:
        for obj in (self.context, self._browser):
            try:
                obj and obj.close()
            except Exception:  # noqa: BLE001
                pass
        if self._pw:
            self._pw.stop()
        self.page = self.context = self._browser = self._pw = None

    # ---- auth ---------------------------------------------------------------------------------------------------------
    def login_as(self, persona: str) -> "UiSession":
        p = self.cfg.personas[persona]
        self.page.goto("/login")
        self.page.select_option(S.LOGIN["role"], p["login_role"])
        self.page.click(S.LOGIN["submit"])
        self.page.wait_for_load_state("networkidle")
        q = parse_qs(urlparse(self.page.url).query)
        self.identity = {"role": (q.get("role") or [p["login_role"]])[0], "user": (q.get("user") or [p["user"]])[0]}
        return self

    def logout(self) -> None:
        """ECS has no logout endpoint (identity lives in the URL). Logging out = discarding identity + cookies."""
        self.context.clear_cookies()
        self.identity = {}
        self.page.goto("/login")

    # ---- navigation ---------------------------------------------------------------------------------------------------
    def goto(self, path: str, **params: str) -> None:
        q = {**self.identity, **params}
        sep = "&" if "?" in path else "?"
        qs = "&".join(f"{k}={v}" for k, v in q.items() if v)
        self.page.goto(f"{path}{sep}{qs}" if qs else path)
        self.wait_loaded()

    def wait_loaded(self) -> None:
        self.page.wait_for_load_state("networkidle")

    def sidebar_link(self, label: str) -> None:
        self.page.get_by_role("link", name=re.compile(re.escape(label), re.I)).first.click()
        self.wait_loaded()

    # ---- forms / dropdowns / upload -----------------------------------------------------------------------------------
    def fill_form(self, fields: dict[str, str], *, scope: str = "") -> None:
        for sel, val in fields.items():
            loc = self.page.locator(f"{scope} {sel}".strip())
            tag = loc.first.evaluate("e => e.tagName.toLowerCase()")
            loc.first.select_option(val) if tag == "select" else loc.first.fill(val)

    def select(self, selector: str, value: str) -> None:
        self.page.select_option(selector, label=value)

    def upload_files(self, selector: str, paths: Iterable[str | Path]) -> None:
        self.page.set_input_files(selector, [str(p) for p in paths])

    def upload_evidence_via_modal(self, file_path: str | Path, **fields: str) -> str:
        """Fills the shared evidence-upload modal (partials/evidence_upload_modal.html) and returns the visible success text."""
        m = S.UPLOAD_MODAL
        for key in ("framework", "application", "control", "owner", "type", "cycle", "comments"):
            if fields.get(key):
                self.fill_form({m[key]: fields[key]})
        self.upload_files(m["file"], [file_path])
        self.page.click(m["submit"])
        self.page.wait_for_selector(f'{m["success"]}, {m["error"]}', state="visible")
        return self.page.inner_text(m["success"]) if self.page.is_visible(m["success"]) else self.page.inner_text(m["error"])

    def submit_bulk_upload(self, paths: Iterable[str | Path]) -> None:
        self.upload_files(S.BULK_UPLOAD["files"], paths)
        self.page.click(S.BULK_UPLOAD["submit"])
        self.wait_loaded()

    # ---- tables / search / filtering -----------------------------------------------------------------------------------
    def table_rows(self, table_selector: str = S.GENERIC["table"]) -> list[list[str]]:
        rows = self.page.locator(f"{table_selector} tbody tr")
        return [[c.strip() for c in rows.nth(i).locator("td").all_inner_texts()] for i in range(rows.count())]

    def table_headers(self, table_selector: str = S.GENERIC["table"]) -> list[str]:
        return [h.strip() for h in self.page.locator(f"{table_selector} thead th").all_inner_texts()]

    def search(self, text: str, *, input_selector: str = 'input[name="q"]') -> None:
        self.page.fill(input_selector, text)
        self.page.press(input_selector, "Enter")
        self.wait_loaded()

    def apply_filter(self, label_or_selector: str, value: str) -> None:
        loc = (self.page.locator(label_or_selector) if label_or_selector.startswith(("#", ".", "[", "select"))
               else self.page.get_by_label(label_or_selector))
        loc.first.select_option(label=value)
        self.wait_loaded()

    # ---- dashboard / drill-down / modal ---------------------------------------------------------------------------------
    def widget_text(self, heading: str) -> str:
        return self.page.get_by_text(re.compile(re.escape(heading), re.I)).first.locator("xpath=ancestor::*[self::div or self::section][1]").inner_text()

    def kpi_value(self, label: str) -> str:
        return self.widget_text(label)

    def drill_down(self, trigger: str) -> str:
        """Click an element (text or selector) that opens the universal drill-down modal; return the modal body text."""
        (self.page.locator(trigger) if trigger.startswith(("#", ".", "[")) else self.page.get_by_text(trigger).first).click()
        self.page.wait_for_selector(S.DRILLDOWN["modal"], state="visible")
        return self.page.inner_text(S.DRILLDOWN["body"])

    def close_modal(self) -> None:
        self.page.keyboard.press("Escape")

    # ---- notifications / download / role visibility ----------------------------------------------------------------------
    def notifications(self) -> list[str]:
        return [t.strip() for t in self.page.locator(S.NOTIFICATIONS["feed_item"]).all_inner_texts()]

    def notice_banner(self) -> str:
        q = parse_qs(urlparse(self.page.url).query)
        return (q.get("notice") or [""])[0]

    def download(self, click_selector_or_text: str) -> Path:
        with self.page.expect_download() as dl:
            (self.page.locator(click_selector_or_text) if click_selector_or_text.startswith(("#", ".", "[", "a", "button"))
             else self.page.get_by_text(click_selector_or_text).first).click()
        target = (self.artifacts_dir or Path(".")) / dl.value.suggested_filename
        dl.value.save_as(str(target))
        return target

    def is_visible_text(self, text: str) -> bool:
        return self.page.get_by_text(re.compile(re.escape(text), re.I)).first.is_visible()

    def nav_labels(self) -> list[str]:
        return [t.strip() for t in self.page.locator("nav a, aside a, .sidebar a").all_inner_texts() if t.strip()]

    def screenshot(self, name: str) -> Path | None:
        if not (self.page and self.artifacts_dir):
            return None
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        path = self.artifacts_dir / f"{name}.png"
        self.page.screenshot(path=str(path), full_page=True)
        return path
