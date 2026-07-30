# Phase-2 Reusability & Intelligence Report

## Reused existing modules

- `CommonControls/` + `common_controls_catalog.py` + `common_controls_collector.py`
- `phase2_reusability.py` / `phase2_tech_adapters.py` (encryption simulation)
- Ops + AI evidence repositories, custody, hashing/versioning
- `evidence_reuse_service.STALE_AFTER_DAYS`, `app.evidence_intel.reuse.score_reuse`
- `ecs_platform.llm_engine.provider.get_provider` (fallback when unconfigured)
- CEQ preset catalog (`common_evidence_presets.py`)
- Evidence Dashboard (`module_capabilities._evidence_dashboard_view`)

## Classification

| Item | Class |
|------|-------|
| `config/phase2_application_portfolio.yaml` | **CONFIGURATION** |
| `data/phase2-reusability/fixtures/**` | **CONFIGURATION** |
| `phase2_tech_adapters.py` (SC/LP normalization, mysql LP fixture) | **REUSABLE_ADAPTER** |
| `phase2_reusability.py` (fixture-gated tech selection) | **CORE_ECS_CHANGE** |
| `phase2_intelligence.py` | **CORE_ECS_CHANGE** |
| Evidence dashboard API + module view `phase2_leadership` | **CORE_ECS_CHANGE** |
| CEQ preset `phase2_evidence_by_app_control` | **CORE_ECS_CHANGE** |

## Use-case status

| # | Use case | Status |
|---|----------|--------|
| 1 | Secure Configuration | **PASS** (3 apps × linux/k8s fixtures) |
| 2 | Least Privilege | **PASS** where tech bindings exist |
| 3 | Completeness COMPLETE/MISSING/STALE | **PASS** (deterministic bindings) |
| 4 | Similarity/reuse gating | **PASS** (SHA exact; similarity ≠ compliance) |
| 5 | Quality scoring | **PASS** (deterministic components/reasons) |
| 6 | AI summaries | **PASS** (LLM abstraction + fallback, no Ollama in tests) |
| 7 | NL audit query metadata | **PASS** (CEQ preset + list filter) |
| 8 | Leadership dashboard | **PASS** (extended Evidence Dashboard API) |
| 9 | Deterministic validation (4 controls) | **PASS** (Phase-1 manifests) |

## Remaining (16/20 GB / live validation)

- Live connector probes (Aurora/Aerospike/K8s) beyond fixtures
- Automatic PGVector indexing of every Phase-2 upload path
- Full LLM-backed summaries in demo (needs configured provider)
- Semantic RAG recall quality under production corpus size
