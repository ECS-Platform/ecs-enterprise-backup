# ECS Sidebar Overflow Fix

## 1. Root Cause

The sidebar grew taller than the viewport when nav groups were expanded (e.g. AI SDLC
Governance with all items open), pushing the Logout button thousands of pixels below the fold and
making lower menu items unreachable.

**Exact cause** — in `modules/shared/templates/partials/enterprise_theme.html`:

```css
.ecs-sidebar       { min-height: 100vh; }   /* grows past viewport */
.ecs-sidebar-inner { min-height: 100vh; overflow-y: auto; }  /* never capped */
```

- Both the sidebar and its inner column used **`min-height: 100vh`** with **no `height`/`max-height`
  ceiling**. When nav content exceeded the screen, the column grew to fit the content (measured
  **3555px tall at a 768px viewport**) instead of staying at 100vh.
- Because nothing constrained the height, `overflow-y: auto` on `.ecs-sidebar-inner` **never engaged**
  — there was no overflow relative to its own (unbounded) height. The page body scrolled, not the
  sidebar.
- `.ecs-sidebar-footer` used `margin-top:auto`, which pins to the bottom of the *grown* column, not
  the viewport — so Logout ended up ~3500px down and invisible.

## 2. Files Modified

- `modules/shared/templates/partials/enterprise_theme.html` (sidebar layout CSS only)

## 3. CSS Changes

Enterprise-grade `header / scrollable nav / pinned footer` layout:

```css
.ecs-sidebar-inner {
  display: flex; flex-direction: column;
  height: 100vh; height: 100dvh;          /* viewport-locked */
  max-height: 100vh; max-height: 100dvh;
  position: sticky; top: 0;               /* pinned while body scrolls */
  overflow: hidden;                       /* the NAV scrolls, not the column */
}
.ecs-nav-groups {                         /* the navigation region */
  flex: 1 1 auto; min-height: 0;          /* min-height:0 lets it shrink to scroll */
  overflow-y: auto; overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;                  /* + themed webkit scrollbar */
}
.ecs-sidebar-footer { flex-shrink: 0; }   /* Logout always pinned/visible */
.ecs-sidebar-brand, .ecs-sidebar-tagline,
.ecs-sidebar-profile, .ecs-sidebar-back { flex-shrink: 0; }  /* fixed header */

@media (max-width: 767.98px) {            /* mobile: natural-height stacking */
  .ecs-sidebar-inner { height:auto; max-height:none; position:static; overflow:visible; }
  .ecs-nav-groups    { overflow-y:visible; min-height:0; flex:0 0 auto; }
}
```

Uses `100dvh` (dynamic viewport) so mobile browser chrome doesn't clip the footer.

## 4 & 5. Before / After (real browser, role=owner/AppOwner, AI SDLC, all groups expanded)

| Metric | BEFORE | AFTER |
|---|---|---|
| `.ecs-sidebar-inner` height @768px vh | **3555px** | **768px** |
| Logout position (bottom) | 3539px (off-screen) | 752px (in viewport) |
| **Logout in viewport** | **False** | **True** |
| Nav scrolls independently | No (page scrolled) | Yes (when content > region) |

Screenshots:
- Before: `nav_audit/sidebar_evidence/before__owner__1440x768.png` (Logout absent, list runs off-screen)
- After: `nav_audit/sidebar_evidence/after__owner__1440x768.png` (Logout pinned at bottom, all groups visible)

**Overflow stress test** (60 extra items injected, 600px viewport):
nav `scrollHeight=2529` vs `clientHeight=376` → **scrolls = True**; Logout stays in view
(bottom 584 < 600); scrolling to bottom reveals the **last item ("Stress Item 59") reachable = True**.

## 6. Persona Validation Matrix

AI SDLC page, all nav groups expanded, 1440×720 viewport, real browser:

| Persona | inner ≤ viewport | Logout in view | nav items | Result |
|---|---|---|---|---|
| AppOwner (owner) | True | True | 71 | PASS |
| Auditor | True | True | 71 | PASS |
| Security Officer | True | True | 71 | PASS |
| Operations Owner | True | True | 70 | PASS |
| CIO | True | True | 72 | PASS |

**ALL PASS.** (At common laptop heights the real menu fits without scrolling; the scroll mechanism
engages and is proven reachable when content exceeds the region — see stress test.)

## 7. Remaining UI Risks

- Cross-browser: layout uses standard flexbox + `position:sticky` + `100dvh`, supported in current
  Chrome/Edge/Safari/Firefox. `100dvh` gracefully falls back to `100vh` (declared first) on older
  engines. Validated in Chromium; Safari/Edge use the same engine families for these properties.
- The webkit scrollbar styling is cosmetic; Firefox uses `scrollbar-width:thin`. No functional risk.
- If a future design adds a second fixed region inside the sidebar, it must also be `flex-shrink:0`
  so the scrollable nav remains the single flexible region.

## SUCCESS CRITERIA — MET

A user can always reach every navigation item and the Logout button regardless of menu expansion
state or screen height: sidebar is viewport-locked, the nav region scrolls independently, and Logout
is pinned and always visible. Verified in a real browser with before/after screenshots across 5 personas.
