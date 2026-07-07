# ECS Audit LLM — Server-Side Processing

How the server processes an audit LLM request end to end. All code lives in
`modules/audit_intelligence/llm/` and **reuses** the existing ECS LLM/RAG/data
layers (it does not duplicate them).

> Design: [audit_llm_prompt_workbench_design.md](../workbenches/audit_llm_prompt_workbench_design.md).
> API surface: [DEVELOPER/…] / see `/api/audit-llm/*` below.

---

## 1. Modules

| File | Responsibility |
|------|----------------|
| `llm/prompt_library.py` | Load + validate `audit_llm_prompt_library.yaml` and `audit_llm_benchmark_profiles.yaml`; lookups. |
| `llm/query_classifier.py` | Classify query (deterministic/llm_assisted/hybrid/unsupported) + extract entities. |
| `llm/deterministic_router.py` | DB-first answers reusing governance + audit-intelligence engines. |
| `llm/context_builder.py` | Assemble deterministic + RAG context (reuses `EvidenceRetriever`). |
| `llm/token_estimator.py` | Token estimate (chars/4) + RAM/token-profile compatibility. |
| `llm/execution_service.py` | Orchestrator: classify → route → context → estimate → LLM/fallback. |
| `llm/benchmark_runner.py` | RAM-aware benchmark + Markdown/JSON export. |
| `routes/routes_audit_llm.py` | `/api/audit-llm/*` JSON endpoints. |

Reused existing modules: `ecs_platform.llm_engine` (`get_provider`,
`EvidenceRetriever`, `set_benchmark_generation_config`), `config/llm.yaml`,
`benchmarks.ai_workload.realistic_prompt_factory.estimate_tokens`,
`modules.audit_intelligence.services.dashboard_service` +
`audit_repository_service`, `modules.governance.engines.missing_evidence_engine`.

---

## 2. Prompt library loader

`load_prompt_library(force=False) -> {prompts, order, errors, count, defaults}`.
Validates each entry against `REQUIRED_FIELDS`, `VALID_QUERY_TYPES`,
`VALID_TOKEN_PROFILES`. Malformed entries are recorded in `errors` and skipped if
missing core fields — the app never crashes on a bad YAML row. Cached in-process;
`reset_cache()` clears it.

## 3. Query classifier

`classify(query) -> {query_type, confidence, signals, entities, reason}`.
Keyword heuristics implement the deterministic-vs-LLM policy. `extract_entities`
returns application, framework, severity, date_range, status, owner, technology,
control, region, phase — all deterministic (no LLM).

## 4. Deterministic query router

Reusable functions (each returns `{answer_text, count, rows, by_*, data_used,
source_references}` and never raises):
`open_observations_by_application`, `observations_till_date`,
`high_risk_observations`, `observations_by_severity/framework/status`,
`aging_observations`, `overdue_observations`, `repeat_observations`,
`closure_trend`, `evidence_gaps`, `framework_highest_gap`,
`audit_readiness_score`, `evidence_completeness`, `stale_evidence`,
`application_comparison`, `evidence_pack_availability`,
`app_owner_pending_actions`. `build_deterministic_context(prompt_id, entities)`
routes via `PROMPT_ROUTES`.

Data sources (existing): governance `missing_evidence_engine.get_all_missing_evidence`
(app-centric demo rows), audit `dashboard_service` (readiness/risk/freshness),
`audit_repository_service` (repository stats, packs).

## 5. RAG / context builder

`build_context(prompt, user_query, entities, deterministic_result, top_k, use_rag)
-> {assembled_prompt, system_prompt, rag_used, source_references, ...}`. RAG uses
the existing `EvidenceRetriever` when a vector store + embeddings exist; otherwise
it degrades to deterministic-only context. Evidence is rendered as citable `[E#]`
blocks (reusing the ECS convention).

## 6. Local LLM provider integration

Execution reuses `ecs_platform.llm_engine.get_provider()` — config-selected
(`config/llm.yaml`), **local Ollama by default** (`qwen3:8b`). RAM-aware limits
(`num_ctx`, `num_predict`, `timeout`) are supplied via the existing
`set_benchmark_generation_config()` (provider still owns the final value:
env > benchmark config > yaml). If the provider is unavailable, execution returns
the deterministic result + a `[FALLBACK]` message (`fallback_used=true`) — never a
crash.

## 7. Prompt execution service

`execute(prompt_id, user_query, input_variables, ram_profile, token_profile,
provider_model, use_rag)` returns:

```
query, prompt_id, query_type, classification, entities,
deterministic_result, evidence_context, assembled_prompt, system_prompt,
llm_response, confidence, assumptions, limitations, source_references, rag_used,
token_estimate, latency_ms, provider_status, fallback_used,
ram_profile, benchmark_profile, token_profile, execution_mode,
memory_warning, warnings
```

The API contract surfaces these by name: `prompt_id, query_type,
deterministic_result, evidence_context, llm_response, provider_status,
fallback_used, token_estimate, latency_ms, benchmark_profile, memory_warning,
assumptions, limitations, source_references`. (`benchmark_profile` mirrors
`ram_profile`; `evidence_context` bundles the deterministic result + RAG/source
references; `memory_warning` is the extracted memory/swap warning, falling back to
the profile's static guidance.)

Dry-run RAM profile → no LLM call. `llm_assisted` → confidence/assumptions/
limitations scaffolded and enforced by the analytical system prompt.

## 8. Token estimator

`estimate_prompt(system_prompt, assembled_prompt, expected_output_tokens,
token_profile, ram_profile)` → input/output/total tokens, context budget,
`fits_context`, and RAM compatibility (`allowed`/`restricted`/`blocked`) + warnings.

## 9. Benchmark runner

`run_benchmark(prompt_ids|category|all_prompts, ram_profile, token_profile,
dry_run)` → structured report; `export_report(report, formats, out_dir)` writes
Markdown + JSON to `reports/audit_llm_benchmarks/`. Captures prompt_id, category,
query_type, token estimate, latency, success/failure, fallback, error_reason,
memory_warning, deterministic_result_count, quality notes, reproducibility.

## 10. API endpoints

`/api/audit-llm/` (JSON, house response shape):
`GET prompts`, `GET prompts/{id}`, `GET profiles`, `POST classify`,
`POST token-estimate`, `POST query`, `POST benchmark`, `GET benchmark/results`,
`POST benchmark/export`.

## 11. Safety

- No secrets/IPs/model names hardcoded (config/env driven).
- No crash on missing LLM / missing RAG / bad YAML / bad input.
- Deterministic results are never altered by the LLM (policy + system prompts).
- Dry-run path is fully offline (safe on any machine).
