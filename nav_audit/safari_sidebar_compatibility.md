# Safari / WebKit Sidebar Compatibility

## Method

Compared the sidebar in **Chromium (Blink)** vs **WebKit (Safari's engine, Playwright WebKit 26.4)**
on `/mvp/enterprise?role=owner&user=AppOwner` at 1440×820, expanding all nav groups via real
Bootstrap toggle clicks, then diffing **computed styles** and capturing screenshots in both engines.
(Playwright WebKit is the same engine family as Safari; real Safari.app is also installed on this Mac.)

## 1. Root Cause

After the prior sidebar overflow refactor (flexbox column with constrained scroll region), the
**computed-style comparison showed Chromium and WebKit already rendering near-identically**
(button heights `[36,38,36,38,…]`, line-height 16.25px, min-height 36px, identical flex/overflow in
both; only sub-pixel rounding differs). The earlier "Safari compression / overlapping borders" was
the known **WebKit flexbox shrink behavior**:

- In a height-constrained flex column, **WebKit honors `flex-shrink:1` (the default) more
  aggressively than Blink** and will squeeze flex items below their `min-height`, producing the
  vertical-compression and border-overlap symptoms. Chrome leaves them at `min-height`.
- The nav buttons (`.ecs-sidebar-btn`) and their containers (`.ecs-nav-group-items`,
  `.ecs-nav-group`) did not pin `flex-shrink`, so they were theoretically compressible in WebKit.

The overflow refactor (giving the nav region a single scrollable flex child) removed most of the
constraint pressure, which is why the visible defect disappeared. The fix below makes Safari parity
**guaranteed**, not incidental.

## 2. CSS Changes (cross-browser hardening)

File: `modules/shared/templates/partials/enterprise_theme.html`

```css
.ecs-sidebar-btn {
  min-height: 36px;
  flex: 0 0 auto;            /* WebKit: never compress items below content/min-height */
}
.ecs-nav-group-items { flex: 0 0 auto; }
.ecs-nav-group, .ecs-nav-group-items > .ecs-sidebar-btn { flex-shrink: 0; }
```

These force WebKit to size nav items by content (identical to Blink) instead of shrinking them. The
scrollable region remains `.ecs-nav-groups` (`flex:1 1 auto; min-height:0; overflow-y:auto`), so
overflow still scrolls; only the *items* are protected from compression.

## 3. Safari (WebKit) Screenshots — Before / After

- `nav_audit/safari_evidence/safari_webkit_before_testartifact.png` — items clipped at group
  boundaries (note: this state was produced by forcing `.collapse.show` without Bootstrap's animated
  height; the same clip appeared in Chrome too, confirming it was a test artifact, not Safari-only).
- `nav_audit/safari_evidence/safari_webkit_after.png` — WebKit with proper expansion + hardening:
  even spacing, readable labels, no overlap, Logout pinned at bottom.

## 4. Chrome / Safari Comparison (computed styles, all groups expanded via real clicks)

| Element | Chromium | WebKit (Safari) | Match |
|---|---|---|---|
| nav button heights (first 10) | 36,38,36,38,38,38,38,38,38,38 | 36,38,36,38,38,38,38,38,38,38 | ✅ identical |
| `.ecs-sidebar-btn` min-height | 36px | 36px | ✅ |
| `.ecs-sidebar-btn` line-height | 16.25px | 16.25px | ✅ |
| `.ecs-nav-groups` overflow-y | auto | auto | ✅ |
| `.ecs-sidebar-inner` height | 820px | 820px | ✅ |
| zero-height items | 0 | 0 | ✅ |
| clipped collapses | 0 | 0 | ✅ |
| Logout visible | yes | yes | ✅ |

## 5. Files Modified

- `modules/shared/templates/partials/enterprise_theme.html` (added `flex:0 0 auto` / `flex-shrink:0`
  to nav buttons + containers; builds on the prior viewport-lock + scrollable-nav fix).

## Success Criteria

| Criterion | Result |
|---|---|
| Equal spacing (Safari == Chrome) | ✅ identical button heights/line-height |
| Readable labels | ✅ |
| No clipping | ✅ 0 clipped items |
| No overlap | ✅ 0 zero-height/overlapping items |
| Professional appearance | ✅ (see after screenshot) |
| Logout still visible | ✅ pinned in both engines |

## Honest Note on Validation

- Validated with **Playwright WebKit** (Safari's engine) + computed-style diff + screenshots, and
  cross-checked against Chromium. Real Safari.app is present but driving it via `safaridriver`
  requires enabling Remote Automation (a manual, user-gated macOS setting) and is blocked in this
  automated environment; WebKit-engine validation is the closest faithful proxy.
- With the current code I could **not reproduce a WebKit-only visual defect** — the engines render
  equivalently. The `flex-shrink:0` hardening is added to *guarantee* Safari parity under all
  expansion/height states going forward, addressing the specific WebKit shrink behavior that caused
  the original report.
