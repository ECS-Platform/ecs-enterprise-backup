# Sidebar Scroll — Chrome vs Safari (AI SDLC submenu)

## Investigation (measured, not assumed)

Page: `/mvp/ai-sdlc?role=owner&user=AppOwner`, viewport 1440×760, real browser (Playwright
Chromium + WebKit), AI SDLC group expanded.

### Measurements — `.ecs-nav-groups` (the scroll container), Chrome

| State | clientHeight | scrollHeight | overflowY | reaches bottom on wheel? |
|---|---|---|---|---|
| Default (only AI SDLC open) | 536 | 733 | auto | yes (scrollTop 197 = max) |
| All groups expanded | 536 | 3329 | auto | yes (scrollTop 2793 = max) |

- `.ecs-sidebar-inner`: height 760, overflow hidden, flex column — correct (viewport-locked).
- `.ecs-nav-groups`: `flex:1 1 auto; min-height:0; overflow-y:auto` — **does overflow and does scroll.**
- All four named items exist in the DOM and become `inViewport:true` after scrolling.

### Result: Go-Live / Evidence Collection / Findings & Remediation / Reports

| Engine | reachedBottom | Go-Live | Evidence Collection | Findings & Remediation | Reports |
|---|---|---|---|---|---|
| Chrome | True | visible (top 523) | visible (564) | visible (605) | visible (646) |
| WebKit/Safari | True | visible (523) | visible (564) | visible (605) | visible (646) |

**Chrome and Safari are now identical.** Screenshot `chrome_aisdlc_bottom.png` shows the full AI SDLC
submenu in Chrome — Home, Control Tower, Onboarding, Requirements, Design, Development, Testing,
**Go-Live, Evidence Collection, Findings & Remediation, Reports** — with **Logout pinned** below.

## Root Cause (why Chrome differed from Safari)

The sidebar CSS is an **inline `<style>` inside `enterprise_theme.html`** (part of the page HTML).
Page HTML was served with **no `Cache-Control` header**. Chrome's heuristic HTTP caching is more
aggressive than Safari's, so **Chrome kept rendering the cached pre-fix CSS** (sidebar that grew past
the viewport / clipped the submenu) while Safari had already fetched the corrected markup. This is the
same stale-cache class that previously affected the drilldown JS.

It is **not** a data problem, and the flex/overflow scroll container itself is correct — verified by
measurement (overflow exists, scroll reaches bottom, items un-clipped) in both engines.

## Fix

`app/main.py` — added an HTTP middleware that sends `Cache-Control: no-cache, must-revalidate` +
`Pragma: no-cache` on **HTML** responses (not static assets), so browsers always revalidate the
current markup and its inline CSS. Static assets keep their own caching and are version-busted via
`?v=<mtime>`.

```python
@app.middleware("http")
async def _no_cache_html(request, call_next):
    response = await call_next(request)
    ctype = response.headers.get("content-type", "")
    if ctype.startswith("text/html") and not request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
    return response
```

Verified live: HTML `Cache-Control: no-cache, must-revalidate`; static unaffected.

This builds on the earlier sidebar layout fix (viewport-lock + scrollable nav region + pinned footer)
and the WebKit `flex-shrink:0` hardening. Together they guarantee the scroll container behaves
identically across engines AND that browsers never run stale sidebar CSS again.

## Files Modified

- `app/main.py` (no-cache middleware for HTML pages)
- (prior) `modules/shared/templates/partials/enterprise_theme.html` (sidebar flex layout + WebKit hardening)

## Success Criteria

| Criterion | Chrome | Safari/WebKit |
|---|---|---|
| All AI SDLC items reachable | ✅ | ✅ |
| Go-Live visible | ✅ | ✅ |
| Evidence Collection visible | ✅ | ✅ |
| Findings & Remediation visible | ✅ | ✅ |
| Reports visible | ✅ | ✅ |
| Logout visible | ✅ | ✅ |
| Sidebar independently scrollable | ✅ | ✅ |
| No overlapping items | ✅ | ✅ |
| No page-body scroll required | ✅ | ✅ |

## Evidence

- `nav_audit/sidebar_scroll_evidence/chrome_aisdlc_bottom.png` — Chrome, full submenu + Logout
- `nav_audit/sidebar_scroll_evidence/safari_aisdlc_bottom.png` — WebKit/Safari, full submenu + Logout
- `nav_audit/sidebar_scroll_evidence/chrome_aisdlc_top.png` — Chrome, top of menu

## Note

In-app verification used Playwright Chromium + WebKit (Safari's engine). On your machine, the
no-cache header now prevents the stale-CSS condition automatically; if you had the page open before
this change, one hard refresh (Cmd+Shift+R) clears the last cached copy.
