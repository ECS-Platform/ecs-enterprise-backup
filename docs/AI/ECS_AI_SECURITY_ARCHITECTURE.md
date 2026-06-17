# ECS AI Security Architecture

**Type:** Security documentation. **No code changed.** Grounding in `ecs_platform/rag.py` (RBAC-before-model), `ecs_platform/rbac/policy.py`, `app/auth/*`, `config/llm.yaml`, `config/repository.yaml`, `provider.py`. Items not enforced in code are marked **[Target]**.

---

## 1. Threat model (AI-specific)

| Threat | ECS mitigation | Status |
|---|---|---|
| Data exfiltration via LLM | Local default (no egress); RBAC pre-filter limits what is retrieved | [Implemented] |
| Over-broad data exposure | Scope filter before model; restricted role w/o assignments sees nothing | [Implemented] |
| Hallucination / fabricated controls | Grounding gate + mandatory citations + refusal sentence | [Implemented] |
| Prompt injection | Grounded-only context; system rules; think-strip | [Partial] |
| Secret leakage | Keyless local / `*_API_KEY` via secret store; never logged | [Implemented] |
| PII exposure to cloud | Data-classification gate before enabling cloud | [Target/Process] |
| Model tampering | On-prem model control; provider allowlist | [Process] |

## 2. Data classification

| Class | Example | LLM handling |
|---|---|---|
| Restricted (evidence, audit) | evidence content, audit_log | **Local only** recommended; never auto-sent to cloud |
| Internal (governance metrics) | coverage %, gaps | Local; cloud acceptable with DPA |
| Public (KPI definitions) | glossary | Any provider |

Classification gating between cloud/local is a **[Process/Target]** today (single global provider); see [Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md).

## 3. Prompt security

- **System prompt** (`prompt_builder.SYSTEM_PROMPT`) enforces: use only supplied evidence; cite every claim; exact refusal when ungrounded; no chain-of-thought.
- **Context minimization:** only RBAC-scoped, retrieved evidence reaches the model.
- **Output sanitation:** `_strip_think` removes `<think>` blocks.
- **Grounding gate** runs before any model call (`rag.py:637-640`).
- **[Target]** dedicated prompt-injection/jailbreak filter + allow/deny lists.

## 4. RBAC (authorization before AI)

- `_rbac_filter` (`rag.py:388-399`) maps UI role → `rbac.yaml` role; `RbacPolicy.authorize("read_evidence")` returns a scope filter applied **before** retrieval.
- Restricted role with empty assignments → **deny** (`rag.py:472-474`).
- Same canonical RBAC (`config/rbac.yaml`, 9 roles) + page/mutation guards govern AI routes.
- Response exposes the RBAC decision (`rbac` field) for auditability.

## 5. PII controls

| Control | Status |
|---|---|
| Minimize data sent to model (RBAC + retrieval) | [Implemented] |
| Local processing (no third-party PII exposure) | [Implemented] (local default) |
| Evidence-access logging | [Implemented] (`repository.yaml: log_evidence_access`) |
| PII detection/redaction before prompt | [Target] |
| Right-to-erasure (drop evidence → re-index) | [Partial] (hash-based reindex drops orphaned chunks) |

## 6. Audit logging

- Governance actions + evidence access written to `audit_log`; last 500 events indexed into RAG for traceable Q&A.
- Each AI answer returns citations (UID, source, timestamp) enabling **answer reconstruction**.
- Index provenance: `doc_kind` + `content_hash` per chunk.
- **[Target]** dedicated immutable/signed prompt+response audit table.

## 7. Encryption

| Layer | Control | Status |
|---|---|---|
| In transit (cloud providers) | HTTPS to provider endpoints | [Implemented] |
| In transit (local Ollama) | host-loopback / cluster network | [Deploy choice] |
| At rest (evidence repo) | Postgres storage encryption | [Deploy/Infra] |
| At rest (object store) | `MINIO_SECURE=true` + TLS in prod | [Deploy] |
| At rest (vectors) | pgvector DB storage encryption | [Deploy/Infra] |
| Secrets | env/secret manager, not in YAML/git | [Implemented] |

## 8. Model security

| Control | Detail | Status |
|---|---|---|
| Keyless local model | No API key to leak (Ollama) | [Implemented] |
| Provider allowlist | Only 5 registered providers | [Implemented] |
| Model pinning | Pin `qwen3:8b` / embedding model via config | [Implemented] |
| Supply-chain (model provenance) | Pull from trusted registry; verify | [Process] |
| Isolation | Run Ollama on controlled host/network | [Deploy] |
| No training on bank data | Local inference only; cloud per vendor DPA | [Implemented local] / [Process cloud] |

## 9. Air-gap security posture

Local provider is fully air-gappable (keyless, no egress; pre-pulled models). In air-gap, disable cloud providers entirely. Non-AI connectors needing egress (Teams/Prisma/Figma) are out of scope and independently gated.

---

## 10. Security control summary

| Domain | Implemented | Target |
|---|---|---|
| Authorization (RBAC pre-model) | ✅ | — |
| Data minimization | ✅ | classification routing |
| Anti-hallucination | ✅ | confidence scoring |
| On-prem / no egress | ✅ (local default) | — |
| Secrets | ✅ | — |
| Audit | ✅ governance + citations | signed prompt/response log |
| PII | partial | redaction engine |
| Encryption | deploy-configurable | enforce TLS everywhere |

**Cross-links:** [Governance Operating Model](ECS_AI_GOVERNANCE_OPERATING_MODEL.md) · [Functional Requirements](ECS_AI_FUNCTIONAL_REQUIREMENTS.md) · [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) · [Decision Matrix](ECS_LOCAL_VS_CLOUD_LLM_DECISION_MATRIX.md)
