# ECS Audit LLM Prompt Workbench — Design

Design for the **ECS Local LLM Audit Prompt Workbench**: generate, manage,
execute, benchmark, and manually test audit-related LLM prompts using **local
LLMs** on **16 GB and 20 GB** laptops (there is no 28 GB machine).

It is **additive** and **reuses** the existing ECS LLM/RAG/data layers — it does
not redesign ECS or duplicate the LLM provider, RAG retriever, evidence
repository, observation engine, dashboard, or predefined-query engine.

---

## 1. Purpose

Support prompt testing for audit, evidence, observation, compliance, closure,
prediction, summarization, and executive-reporting use cases, with:
- a **prompt library** (40 audit prompts),
- a **query classifier** (deterministic / llm_assisted / hybrid),
- a **deterministic query router** (DB/query logic first),
- a **RAG/context builder** (grounded, cited context),
- **local LLM execution** via the existing provider abstraction,
- a **token estimator** and **RAM-aware benchmark runner** for 16/20 GB.

---

## 2. Architecture (reuse map)

```
Frontend (Jinja2 Workbench, /mvp/audit/llm-workbench)
        │  fetch
        ▼
REST API  /api/audit-llm/*  (routes_audit_llm.py)
        │
        ▼
modules/audit_intelligence/llm/execution_service.execute()
   1. query_classifier.classify()            ── entities + query_type
   2. deterministic_router.build_deterministic_context()
        └─ reuses: governance missing_evidence_engine,
                   audit dashboard_service, audit_repository_service
   3. context_builder.build_context()
        └─ reuses: ecs_platform.llm_engine.EvidenceRetriever (RAG),
                   prompt_builder citation convention
   4. token_estimator.estimate_prompt()
        └─ reuses: benchmarks.ai_workload estimate_tokens (chars/4)
   5. LLM call via ecs_platform.llm_engine.get_provider()  (Ollama default)
        └─ set_benchmark_generation_config() for RAM-aware num_ctx/timeout
        └─ fallback to deterministic result if unavailable

Benchmark: benchmark_runner.run_benchmark() + export_report()
           scripts/run_audit_llm_benchmark.py  -> reports/audit_llm_benchmarks/
Config:    config/audit_llm_prompt_library.yaml
           config/audit_llm_benchmark_profiles.yaml
           config/llm.yaml (existing; provider/model, local Ollama)
```

**Nothing above re-implements the LLM provider, RAG, or data engines** — the new
`modules/audit_intelligence/llm/` package composes them.

---

## 3. Prompt lifecycle

1. Prompt category defined → 2. template stored in the library YAML → 3. template
carries input variables, expected output format, token profile, model guidance →
4. user opens the Workbench → 5. selects category + prompt → 6. enters sample
audit/evidence/observation data → 7. selects a **RAM profile**
(`local_16gb_safe` / `local_20gb_extended` / `worst_case_enterprise_dry_run`) →
8. selects provider/model (config-driven default) → 9. ECS **estimates tokens** →
10. ECS builds **deterministic context** from data → 11. ECS builds **RAG/evidence
context** where applicable → 12. ECS sends the final prompt to the **local LLM** →
13. ECS captures response, latency, token estimate, success/failure, provider
availability, fallback result, memory warning → 14. frontend displays the
response → 15. ECS stores/exports benchmark evidence → 16. tester compares output
quality → 17. prompt refined if needed → 18. **benchmark report** generated for
16/20 GB → 19. **prompt inventory + benchmark results** documented.

---

## 4. Deterministic vs LLM-assisted policy

| query_type | Behaviour |
|------------|-----------|
| **deterministic** | Answered from DB/query logic first (router). The LLM may only *summarize* the deterministic result — it must never change a number/id/status. |
| **llm_assisted** | Analytical/predictive. Uses historical observations, evidence gaps, closure history, severity trends, application/framework/technology metadata + deterministic context. Output **must** include confidence, assumptions, limitations, data used, and source references where available. **Never present a prediction as certainty.** |
| **hybrid** | Deterministic result + LLM explanation (e.g. "How many high-risk observations are open, and summarize the business impact?"). |

The classifier decides via keyword heuristics: pure "how many / list / older than"
→ deterministic; predictive verbs (chance, likelihood, predict, forecast, root
cause) → llm_assisted; a mix, or summarization of ECS data → hybrid.

---

## 5. Query classification design

`query_classifier.classify(query) -> {query_type, confidence, signals, entities, reason}`.
Entities extracted deterministically (no LLM): **application, framework, severity,
date_range, status, owner, technology, control, region, phase**. Vocabularies are
demo-safe (no secrets/IPs). Unknown/empty → `unsupported`.

## 6. Deterministic query router design

`deterministic_router` exposes reusable functions (open observations by
application, by severity/framework/status, aging/overdue, repeat, closure trend,
evidence gaps, audit-readiness score, evidence completeness, stale evidence,
app/framework comparison, evidence-pack availability, app-owner pending actions).
Each returns `{answer_text, count, rows, by_*, data_used, source_references}` and
**never raises**. A `PROMPT_ROUTES` map binds each `prompt_id` to its ground-truth
function. Data sources are the **existing** governance `missing_evidence_engine`
(app-centric demo data: Net Banking / Mobile Banking / Payments) and the
audit-intelligence `dashboard_service` / `audit_repository_service`.

## 7. RAG / context builder design

`context_builder.build_context()` renders the deterministic result as an
LLM-readable block and (when a vector store + embeddings are available) appends
numbered, citable `[E#]` evidence via the existing `EvidenceRetriever`. If RAG is
unavailable (offline / no embeddings) it degrades to deterministic-only context —
never crashing. Source references combine deterministic sources + evidence uids.

## 8. Prompt library design

`config/audit_llm_prompt_library.yaml` holds 40 prompts. Each entry:
`prompt_id, category, name, description, query_type, persona, input_variables,
required_context, system_prompt, user_prompt_template, expected_output_format,
confidence_policy, citation_policy, risk_level, token_profile,
applicable_frameworks, applicable_roles, recommended_model_size,
local_16gb_supported, local_20gb_supported`. Loaded + validated by
`prompt_library.load_prompt_library()` (strict-but-safe: a bad entry is recorded,
not fatal).

## 9. API design

`/api/audit-llm/` (house response shape `{ok, ...}` / `{ok:false, status:error, ...}`):
`GET prompts`, `GET prompts/{id}`, `GET profiles`, `POST classify`,
`POST token-estimate`, `POST query`, `POST benchmark`, `GET benchmark/results`,
`POST benchmark/export`. The `query` response carries: query, query_type,
deterministic_result, assembled_prompt, llm_response, confidence, assumptions,
limitations, source_references, token_estimate, latency_ms, provider_status,
fallback_used, ram_profile, token_profile, warnings.

## 10. Frontend design

`/mvp/audit/llm-workbench` (Jinja2 + Bootstrap, extends `audit/_shell.html`, nav
group "Audit Intelligence → LLM Prompt Workbench"). Inputs: query, category,
prompt, application, framework, severity, date range, RAM profile, token profile,
provider/model. Buttons: classify, estimate tokens, run prompt, run benchmark,
export benchmark. Panels: deterministic result, LLM response, confidence,
assumptions, limitations, source references, latency/token metrics, provider
status, fallback, warnings.

## 11. Token estimation design

`token_estimator.estimate_prompt()` reuses the shared `estimate_tokens` (chars/4)
for input+output+total, compares against the token profile's context budget, and
assesses **RAM/token-profile compatibility** (allowed / restricted / blocked) with
warnings. Pure + offline (dry-run safe on any machine).

## 12. Benchmark design

`benchmark_runner.run_benchmark()` selects prompts (id / category / all), runs
them under a RAM profile in dry-run or LLM mode, captures per-prompt token
estimate, latency, success/failure, fallback, memory warning, and quality notes.
`export_report()` writes Markdown + JSON to `reports/audit_llm_benchmarks/`. The
CLI is `scripts/run_audit_llm_benchmark.py`.

## 13. 16 GB testing strategy

Use for: prompt-library validation, 4K/8K prompts, **selected** 16K prompts
(concurrency 1), low-memory-pressure runs. Avoid: large model + heavy Docker
together; 20K execution (blocked); concurrency > 1. `local_16gb_safe`:
`max_context=8192`, `optional_context=16384`, `max_output_tokens=1024/2048`,
`concurrency=1`, `rpm=1`, `timeout=180`, `top_k=5`.

## 14. 20 GB testing strategy

Use for: 4K/8K/16K prompts, **selected** 20K prompts, benchmark evidence
generation, concurrency 1 (optional 2 only after a stable baseline).
`local_20gb_extended`: `max_context=16384`, `optional_context=20480`,
`max_output_tokens=2048`, `concurrency=1` (optional 2), `rpm=1`, `timeout=240`,
`top_k=8`.

## 15. Local LLM limitations

- Local model quality/latency depends on model size and available RAM.
- 16 GB cannot safely run 20K prompts or a large model alongside a heavy Docker
  stack.
- RAG requires a vector store + embeddings; offline it degrades to
  deterministic-only context.

## 16. Fallback behaviour

If the LLM is unavailable the execution service **does not crash**: it returns the
deterministic result plus a clear `[FALLBACK]` message and `fallback_used=true`.
The `worst_case_enterprise_dry_run` profile never calls the LLM (token estimate +
assembled-prompt metadata + warnings only).

## 17. Evidence / citation policy

Grounded answers cite evidence ids `[E#]` when RAG context is present
(`citation_policy: cite_when_available`). Deterministic summaries carry
`data_used` + `source_references`. The system prompts forbid inventing facts.

## 18. Risk & confidence policy

`llm_assisted` prompts require `confidence` + `assumptions` + `limitations` (the
execution service scaffolds these and the system prompt enforces them).
`risk_level` per prompt guides reviewer attention; predictions are never presented
as certainty.

## 19. Future enhancements

- Persist benchmark results to the durable store; add a results dashboard.
- Tokenizer-accurate counts (vs chars/4) when a tokenizer is available.
- Optional concurrency-2 auto-tuning on 20 GB after a stable baseline.
- Wire additional deterministic routers (framework trends, comparison engine).
- Add SSH/remote local-LLM endpoints where the provider abstraction supports them.
