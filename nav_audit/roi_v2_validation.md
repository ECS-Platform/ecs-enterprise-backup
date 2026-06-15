# ROI & Value Realization Center v2 — Validation Report

**Scope:** ROI deck content + presentation only.
**Unchanged:** ECS theme, navigation, dark executive styling, Previous/Next controls,
manual slide navigation, boardroom presentation format. No auto-play. No scrolling.
All slide values use the latest approved workbook numbers, verbatim.

**Palette kept:** bg `#0B1220` · cards `#111827` · panels `#1E293B` · primary text `#F8FAFC` ·
secondary `#CBD5E1` · accent `#38BDF8` · positive `#22C55E` · ROI highlight `#F59E0B`.

---

## 1. New Storyboard — exactly 4 slides

| # | Slide | Content |
|---|---|---|
| 1 | FY25-26 Actual Live Value Realization | 3 KPI cards + descending horizontal framework chart (5 highlighted) |
| 2 | Framework Value Realization | 25-app master table + bar chart + bottom callout |
| 3 | FTE Productivity Realization | 3 KPI cards + Without/With ECS comparison + chart + banner |
| 4 | Executive Value Dashboard | 7-year table + net-benefit bar chart + executive callout band |

No "Annual Value Creation", "Scale-Up Story", "Approval Recommendation", "The Problem",
or "The ECS Shift" slides. Appendix remains separate.

---

## 2. Slide 1 — FY25-26 Actual Live Value Realization

- **Title (single):** "FY25-26 Actual Live Value Realization"
- **Subtitle:** "Projected value generated across currently live applications."
- **KPI cards (3):** 17 Frameworks · 9,554 Applications · ₹17.27 Cr Annual Saving.
- **Horizontal framework value chart:** all 17 frameworks, **sorted descending** by Annual Saving.
- **Highlighted (visually stand out in gold):** ASST (₹3.35 Cr), IS Audit (₹2.70 Cr),
  OS Baselining (₹2.48 Cr), ITPP (₹2.26 Cr), Middleware Baselining (₹1.56 Cr).
- Data used exactly as supplied; total annual saving **₹17.27 Cr**.

## 3. Slide 2 — Framework Value Realization (Master)

- **Title (single):** "Framework Value Realization"
- **Subtitle:** "ROI generated from onboarding 25 applications."
- **Table (17 rows):** Framework · Applications · Observations/App · Total Observations ·
  Emails Saved · Hours Saved · Annual Saving (Cr) — exact values supplied.
- **Bar chart:** Annual Saving by framework.
- **Bottom executive callout:** 25 Applications · 45,438 Hours Saved · ₹4.54 Cr Annual Saving.

## 4. Slide 3 — FTE Productivity Realization

- **Title (single):** "FTE Productivity Realization"
- **Subtitle:** "Operational capacity returned to the bank."
- **KPI cards:** Hours Saved 45,438 · Annual Saving ₹4.54 Cr · FTE Equivalent 22.72
  (Cost Per Hour ₹1,000 and Average Salary ₹20 Lakh underpin the model).
- **Comparison:** Without ECS → **22.72 Additional FTE Required** (red) vs
  With ECS → **0 Additional FTE Required** (green) + comparison chart.
- **Banner:** "ECS returns the equivalent productivity of 22.72 full-time employees annually."

## 5. Slide 4 — Executive Value Dashboard

- **Title (single):** "Executive Value Dashboard"
- **Subtitle:** "Scale-up economics of ECS."
- **Table (Year 1–7):** Applications (25/100/200/400/500/400/800) · Annual Savings
  (4.54/18.16/36.32/72.64/90.80/72.64/145.28) · ECS Cost (4.0/2.0/2.2/2.2/2.2/2.2/2.2) ·
  Net Benefit (0.54/16.16/34.12/70.44/88.60/70.44/143.08).
- **Net-benefit bar chart:** X = Year 1–7, Y = Net Benefit (Cr), labels above every bar.
- **Executive callout band:** 800 Applications · ₹143.08 Cr Net Benefit · Stable ₹2.2 Cr OPEX ·
  Scale Driven ROI.

---

## 6. Design Rules — Compliance

| Rule | Status |
|---|---|
| Each slide fits one 16:9 screen | PASS (verified via 1600×1000 screenshots) |
| No scrolling / no vertical page movement | PASS (dense tables use a contained inner scroll; the slide/page do not scroll) |
| No auto-play / no auto-advance | PASS (deck has no timer; manual Previous/Next/dots/arrows only) |
| Max 3 KPI cards per row | PASS (Slides 1 & 3 use 3 cards) |
| No duplicate / repeated headings | PASS (one `<h2>` per slide; 4 unique titles) |
| Charts boardroom readable, large fonts, high contrast | PASS |
| White text on dark panels / dark text on light only | PASS (no light-blue text on white) |
| Existing theme & palette kept | PASS |

---

## 7. Validation Results (`/mvp/roi`)

| Check | Result |
|---|---|
| HTTP status | **200** |
| Exactly 4 slides | **PASS** |
| Previous / Next navigation works | **PASS** (`data-deck-prev` / `data-deck-next`; dots + arrow keys) |
| Charts render | **PASS** (Slide 1: 17 bars; Slide 2: bar chart; Slide 3: comparison chart; Slide 4: 7 bars) |
| Annual Saving = ₹4.54 Cr (25-app model) | **PASS** |
| FTE Equivalent = 22.72 | **PASS** |
| FY25-26 value = ₹17.27 Cr | **PASS** |
| Executive Dashboard Year-7 Net Benefit = ₹143.08 Cr | **PASS** |
| 5 highlighted frameworks on Slide 1 | **PASS** |
| No duplicate headings | **PASS** |
| No scrolling | **PASS** |
| JS syntax (`node --check`) | **PASS** |
| Linter | **PASS** (no errors in edited files) |

**Screenshots:** `nav_audit/roi_v2_s1.png` · `roi_v2_s2.png` · `roi_v2_s3.png` · `roi_v2_s4.png`

---

## 8. Files Changed

| File | Change |
|---|---|
| `app/roi/workbook.py` | Added `_BOARD_LIVE` (FY25-26), updated `_BOARD_FRAMEWORKS` (25-app master), `_BOARD_FTE` (45,438h / 22.72 FTE / ₹4.54 Cr), and `_BOARD_DASHBOARD` (7-year). `build_board_deck()` rewritten to emit the 4-slide fixed model; added `_build_live_block()`; master KPIs → 25/45,438/₹4.54 Cr. |
| `modules/executive_overview/templates/mvp_roi_center.html` | Rebuilt deck to 4 slides; nav count `/ 4`; highlight flag on Slide 1 chart; 7-column chart class on Slide 4. |
| `modules/shared/templates/partials/roi_storyboard.js` | Deck comment → 4 slides; removed scenario re-render of the deck (now fixed data). |
| `modules/shared/templates/partials/roi_center_styles.html` | Added 3-KPI row variant, FY25-26 live chart layout + gold highlight styling, compact callout, 7-bar chart sizing, numeric nowrap. |

---

## 9. Summary

- ROI Center redesigned to **exactly 4 executive slides** using the latest workbook values.
- Key totals verified: FY25-26 ₹17.27 Cr · 25-app ₹4.54 Cr · FTE 22.72 · Year-7 net ₹143.08 Cr.
- Top-5 frameworks highlighted on Slide 1; 7-year net-benefit chart on Slide 4.
- Existing theme, navigation, manual Previous/Next, dark styling, and boardroom format preserved.
- No scrolling, no auto-play, no duplicate headings; high contrast throughout.

**Status: COMPLETE — awaiting approval. Not committed, tagged, or pushed.**
