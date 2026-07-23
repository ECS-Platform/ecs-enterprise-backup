# ECS Local LLM Migration Plan (Phase 13)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

> **Framing correction (important).** This is **not** a "build local LLM support" project. ECS already
> defaults to **local Ollama + local pgvector**. This plan is therefore a **validation, hardening, and
> rollout** program to certify the existing local-first design for banking production.

---

## 1. Current State

| Aspect | State | Evidence |
|---|---|---|
| Provider abstraction | Exists (`LLMProvider` + 5 providers) | `provider.py:30-246` |
| Default provider | Local Ollama (keyless) | `config/llm.yaml:7`, `provider.py:157-227` |
| Default model / embeddings | qwen3:8b / nomic-embed-text | `config/llm.yaml:8-9` |
| Vector store | pgvector (local), dim 768 | `config/vectorstore.yaml`, `pgvector_store.py` |
| LLM-using features | RAG assistant + embedding index only | `rag.py:649`, `ingestion.py:213-226` |
| Everything else | Deterministic (no model) | feature inventory (Phase 2) |
| Fallback | Deterministic answers when provider unset | `rag.py:642-648`, `governance.py:709-743` |
| Heavy ML deps | None (stdlib HTTP) | `requirements.txt` |

**Residual cloud touchpoints (optional, opt-in):** OpenAI/Gemini/Anthropic/Azure providers exist but
are not default; some connectors (Teams/Prisma/Figma) are SaaS (non-AI egress).

## 2. Future State (target)

- 100% local AI path certified for air-gapped/on-prem/private-cloud/UAT/prod.
- Code default provider = `ollama` (remove `gemini` fallback ambiguity).
- Validated model + embedding tiers (qwen3:8b default; bge-large optional quality tier).
- Provider health in readiness probes; alerting on fallback mode.
- Documented model-blob vendoring for air-gap.

## 3. Dependencies

| Dependency | Type | Owner |
|---|---|---|
| Ollama daemon (GPU/CPU node) reachable on private net | Infra | Platform/Infra |
| Postgres + pgvector instance | Infra | DBA |
| Model blobs (qwen3:8b, nomic-embed-text[, bge-large]) vendored into air-gap | Supply-chain | Platform |
| Env/config management (`ECS_LLM_*`, `OLLAMA_URL`, `ECS_VECTOR_DIM`) | Config | DevOps |
| RBAC role gaps (if Audit Manager/Risk Owner/etc. required) | App (separate scope) | App team |

## 4. Risks & Mitigations

| Risk | Sev | Mitigation |
|---|---|---|
| Embedding dimension mismatch on model swap | **High** | Treat dim change as a migration: recreate table + full reindex; default nomic (768) needs none |
| Code default falls back to `gemini` if YAML missing | Med | Set `get_provider` default to `ollama` (`provider.py:241`) |
| Cold-start latency | Med | `ECS_OLLAMA_KEEP_ALIVE` + `OllamaProvider.warm()` (already present) |
| Local model quality below cloud for complex synthesis | Med | Reserve bge-large/larger gen models for quality tier; keep deterministic fallback |
| Accidental cloud egress (provider misconfig) | **High (banking)** | Lock `ECS_LLM_PROVIDER=ollama` in prod; network policy blocks AI egress; alert if provider != ollama |
| SaaS connectors (Teams/Prisma/Figma) break air-gap | Med | Disable/replace for air-gapped envs (non-AI) |
| Doc drift (baseline says "no LLM") | Low | Sync `ECS_ARCHITECTURE_BASELINE.md:768` |

## 5. Effort (T-shirt, indicative)

| Workstream | Effort | Notes |
|---|---|---|
| Local stack stand-up (Ollama + pgvector) | S | Infra config |
| Config hardening (default=ollama, prod lock) | S | Small code/config |
| Benchmark + model selection (Phase 10 harness) | M | Per-env measurement |
| Quality gate on 20+ ECS prompts | M | Reviewer rubric |
| Optional embedding upgrade (bge-large + reindex) | M | Only if quality tier needed |
| RBAC role-gap additions (if required) | M–L | Separate scope |
| Air-gap model vendoring + runbook | M | Supply-chain |

## 6. Rollout Strategy

```
Stage 0  Demo (default Ollama, single node) ── validate functionally
Stage 1  UAT (Ollama GPU node + pgvector) ──── run benchmark + quality gate
Stage 2  Pre-Prod / private cloud ─────────── residency review, fallback tests, load test
Stage 3  Production (air-gapped/on-prem) ───── prod-lock provider, vendored blobs, alerting
```

### UAT Strategy
- Deploy Ollama (qwen3:8b) + pgvector on UAT.
- Set `ECS_LLM_PROVIDER=ollama`; verify `/api/platform/rag/status` = configured, `/assistant` returns
  `mode: rag, grounded: true`.
- Run Phase 10 harness; capture P50/P95, tokens/sec, RAM; score quality on ECS prompts.
- Reindex evidence; verify pgvector recall.
- Validate the Phase 12 matrix across all logins/modules.

### Production Strategy
- Air-gapped: vendor model blobs; pin digests; no AI egress (network policy).
- Lock `ECS_LLM_PROVIDER=ollama`; alert if provider changes or fallback engages.
- Keep-alive warm models; provider health in readiness probe.
- Capacity per benchmark; DR runbook for the Ollama node; deterministic fallback remains the safety net.

## 7. Acceptance Criteria

1. All 12 logins resolve and answer via local provider (or deterministic fallback) — Phase 12.
2. RAG assistant returns grounded answers on local Ollama; embeddings index into pgvector locally.
3. No AI egress in air-gapped mode (verified by network policy + logs).
4. Benchmark numbers captured and within agreed SLO; quality gate passed.
5. Deterministic fallback verified when Ollama is stopped.

## 8. Conclusion

Migration risk is **low** because local LLM is already the ECS default. The program is primarily
**certification + hardening + rollout**, with the one true engineering caution being **embedding
dimension management** on any model swap. No mass refactor is required; the existing abstraction is the
correct foundation.
