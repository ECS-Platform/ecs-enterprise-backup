# ECS Benchmark — Demo / Simulation Module

**Branch:** `cursor/predefined-queries-module`
**Change type:** Additive, demo-safe, lightweight. New page + route + one nav item.
**Route:** `GET /mvp/ecs-benchmark`

---

## 1. Purpose

Give senior stakeholders (CIO/MD) a visual walkthrough of how **ECS benchmark execution and capacity-planning evidence** would look inside the platform — an animated benchmark run, live-style runtime metrics, result cards, representative token-sizing scenarios, methodology, and the cost story (original assumption vs benchmark-backed planning).

It is a **presentation surface only**. It shows the shape of the evidence; it does not produce it.

---

## 2. Mock / simulated nature (what is real vs mocked)

| Aspect | Status |
|---|---|
| Benchmark execution | **Mocked** — a client-side timeline driven by JavaScript `setTimeout`. |
| Runtime panel (elapsed / step / progress / status) | **Mocked** — animated in the browser. |
| Result cards (input/output/total tokens, context window, output cap, truncation, GSU, monthly cost) | **Mocked** — deterministic values for the *Small Assessment* demo profile. |
| Scenario table (7 rows) | **Static demo data** — engineering planning + representative measured values. |
| Cost comparison + savings | **Static demo data** — planning figures for stakeholder illustration. |
| Real benchmark logic | **Untouched & not invoked** — lives in `scripts/` (e.g. `run_neev_validation_benchmark.py`, `run_16k_1k_token_validation.py`) with evidence under `benchmark_outputs/` / `docs/benchmarks/`. |

**No live execution of any kind on this screen:** no Docker, no Ollama, no PGVector, no embeddings, no RAG, no object storage, no backend benchmark job. The page route only renders a template with a small static context (no I/O, no LLM calls). The page's own `<script>` contains **zero** network calls (`fetch`/`XMLHttpRequest`/`/api/` count = 0 in `mvp_ecs_benchmark.html`).

> Note: the rendered page still includes the standard shared ECS partials (sidebar, theme, chatbot widget) which have their own unrelated client scripts; the **ECS Benchmark module itself** makes no backend calls.

---

## 3. Page contents

1. **Header** — "ECS Benchmark" / subtitle "AI workload, token sizing, and capacity planning simulation" + `DEMO SIMULATION` badge.
2. **Demo note** — states this is a simulation and points to `scripts/` and `benchmark_outputs/`.
3. **Benchmark Execution** panel — **Start Benchmark** button (+ Reset after a run) and a status chip (Idle / Running / Complete).
4. **Runtime panel** — Elapsed timer, Progress %, Step counter (0/9 → 9/9), striped progress bar, current-step line.
5. **Execution Timeline** — 9 animated steps:
   - Initializing benchmark profile
   - Building prompt via Prompt Builder
   - Loading application/control/framework metadata
   - Generating representative evidence context
   - Applying num_ctx and max_output settings
   - Sending prompt to local LLM provider
   - Capturing input/output token metrics
   - Generating benchmark report
   - Benchmark complete
6. **Benchmark Result cards** — Input / Output / Total tokens, Context Window, Output Cap, Truncation Suspected, Estimated GSU, Estimated Monthly Cost, Profile (populate after a run).
7. **Benchmark Scenarios table** — 7 rows (below).
8. **Methodology** — prompt-construction benchmark, local Ollama token measurement, RAG-informed simulated context, no live RAG/PGVector/object-storage on this screen, enterprise values are planning extrapolations.
9. **Cost Comparison** — original assumption vs benchmark-backed planning + savings.

---

## 4. Benchmark values displayed

### Simulated single-run result (Small Assessment demo profile)
Input 5,157 · Output 311 · Total 5,468 · Context Window 8,192 · Output Cap 512 · Truncation Suspected: No · Estimated GSU 2 · Estimated Monthly Cost ₹4.34 lakh.

### Scenario table

| Scenario | Apps | Timeout | num_ctx | Max Output | Est. Input | Measured Input | Measured Output | Status |
|---|---|---|---|---|---|---|---|---|
| Small Assessment | 1 | 180 sec | 8,192 | 512 | 4,926 | 5,157 | 311 | Measured |
| 16K / 1K Validation | 1 | 600 sec | 16,384 | 1,024 | 25,617 | 16,384 | 1,024 | Measured / Context limited |
| Enterprise Planning | 50 | 600 sec | 40,960 | 3,000 | 50,175 | Planning | Planning | Extrapolated |
| Large Repository 100 Apps | 100 | 600 sec | 40,960 | 3,000 | 50,169 | Planning | Planning | Simulated |
| Large Repository 200 Apps | 200 | 900 sec | 40,960 | 3,000 | 56,393 | Planning | Planning | Simulated |
| Large Repository 500+ Apps | 500+ | 1200 sec | 65,536 | 3,000 | 60,341 | Planning | Planning | Simulated |
| Large Repository 1000+ Apps | 1000+ | 1800 sec | 65,536 | 4,000 | 70,000 | Planning | Planning | Future sensitivity |

### Cost comparison

| Metric | Original assumption | Benchmark-backed planning |
|---|---|---|
| Token profile | 125K in / 50K out | 50K in / 3K out |
| Weighted TPM | 1,725,000 | 231,000 |
| GSU | 11 | 2 |
| Annual cost | ₹2.866 Cr | ₹0.521 Cr |
| **Annual savings** | | **₹2.345 Cr** |
| **Monthly revised cost** | | **₹4.34 lakh/month** |

---

## 5. Files added / modified

### Added
| File | Purpose |
|---|---|
| `modules/shared/templates/mvp_ecs_benchmark.html` | The demo page (Bootstrap 5.3 + self-contained CSS + `setTimeout` simulation JS). |
| `app/routes_ecs_benchmark.py` | Registers `GET /mvp/ecs-benchmark` (render-only; no benchmark/LLM/DB work). |
| `modules/shared/templates/partials/ecs_nav_ecs_benchmark.html` | Left-nav "ECS Benchmark" group partial. |
| `docs/ECS_BENCHMARK_DEMO_MODULE.md` | This document. |

### Modified
| File | Change |
|---|---|
| `app/main.py` | Two lines: import + `register_ecs_benchmark_routes(app, templates)` after the other route registrations. |
| `modules/shared/templates/partials/ecs_nav_groups.html` | One `{% include %}` adding the ECS Benchmark group (group 6) as a first-class, always-visible left-nav item. |

No existing benchmark scripts, Neev logic, AI SDLC module files, or authentication logic were modified.

---

## 6. Route URL

- `http://127.0.0.1:8000/mvp/ecs-benchmark?role=owner&user=AppOwner`

(Reachable for any role; the left-nav "ECS Benchmark → Benchmark Simulation" item links to it.)

---

## 7. Validation

```bash
python -m compileall app modules scripts      # -> exit 0 (clean)
./start_ecs.sh                                 # or uvicorn app.main:app --reload
```

Verified (server run with `ECS_LOCAL_AUTH_BYPASS=true` so demo pages load):

| Check | Result |
|---|---|
| `GET /mvp/ecs-benchmark` | **200** |
| Page content (header, subtitle, Start button, all 9 timeline steps, all 7 scenarios, demo note, methodology, cost section, ₹2.345 Cr, TPM 231,000) | **all present** |
| Left-nav "ECS Benchmark" item on dashboards | **present** (`nav-ecs-benchmark`, `/mvp/ecs-benchmark`) |
| Start Benchmark → simulation (via headless Chrome CDP) | status **Complete**, progress **100%**, step **9/9**, all 9 steps done, result cards populated (input 5,157, GSU 2) |
| Network calls inside `mvp_ecs_benchmark.html` script | **0** (`fetch`/`XMLHttpRequest`/`/api/`) |
| Regression: `/dashboard`, `/dashboard/cio`, `/mvp/ai-sdlc`, `/mvp/ai-sdlc/control-tower`, `/mvp/predefined-queries` | **all 200** |

> Validation used a throwaway `/tmp` virtualenv with the app's already-declared demo deps; no new repo dependency was added and the system Python was not modified.

---

## 8. Confirmations

- **No benchmark scripts modified** — `scripts/run_neev_validation_benchmark.py`, `scripts/run_16k_1k_token_validation.py`, `benchmarks/ai_workload/*`, `docs/benchmarks/*` untouched.
- **No Neev logic modified.**
- **No real Ollama / PGVector / RAG / embeddings / Docker call is made** by this module — the timeline and metrics are browser-side mock data; the route does render-only work.
- **AI SDLC module untouched**; **authentication logic untouched.**
