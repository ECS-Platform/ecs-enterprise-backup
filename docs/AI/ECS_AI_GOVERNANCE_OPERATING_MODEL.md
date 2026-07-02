# ECS AI Governance Operating Model

**Type:** Operating-model documentation. **No code changed.** Describes how AI use cases are governed across their lifecycle. Grounded in `modules/ai_sdlc/*` (AI SDLC governance), `ecs_ai_governance_drilldowns` (posture), `rag.py` (grounding controls), `config/llm.yaml`. Process steps not yet automated are marked **[Process/Target]**.

> ECS already ships the **mechanisms** for AI governance (stage gates, posture scoring, grounding controls, audit log). This operating model wraps them into a lifecycle. Where a step is currently manual/process rather than enforced in code, it is labeled.

---

## 1. AI use-case lifecycle

```
Intake → Risk Assessment → Model Approval → Prompt Approval →
Build/Configure → Validate → Deploy → Monitor → Revalidate → Retire
```

| Stage | What happens | ECS support |
|---|---|---|
| Intake | Register the AI use case (problem, persona, data) | AI Registry (`/mvp/ai-registry`) |
| Risk Assessment | Classify data sensitivity + AI risk | AI Governance posture (6 dims) |
| Model Approval | Approve model + provider for the use case | `config/llm.yaml` change control [Process] |
| Prompt Approval | Review system/RAG prompts | `prompt_builder.SYSTEM_PROMPT` review [Process] |
| Build/Configure | Wire to RAG pipeline | `rag.py` (no new code per UC) |
| Validate | Test grounding, citations, RBAC, refusal | Testing guide + validators |
| Deploy | Select provider per environment | `ECS_LLM_PROVIDER` |
| Monitor | Track posture, hallucination, prompt audits | AI Governance posture |
| Revalidate | Periodic re-review | [Process/Target] |
| Retire | Disable use case / model | registry status [Process] |

## 2. Model approval

| Control | Detail | Status |
|---|---|---|
| Approved model list | Models allowed per environment (default `qwen3:8b` local) | [Process] over `llm.yaml` |
| Provider approval | Local vs cloud per data classification | [Process] (see Decision Matrix) |
| Embedding model approval | dim must match `ECS_VECTOR_DIM` (768) | [Implemented] consistency |
| Change control | Provider/model change = reviewed config change | [Process] |
| Registry record | Model logged in AI Registry | `/mvp/ai-registry` |

## 3. Prompt approval

| Control | Detail | Status |
|---|---|---|
| System prompt review | `SYSTEM_PROMPT` enforces grounding/citation/refusal | [Implemented] |
| RAG prompt assembly review | `_assemble_prompt` / `build_rag_prompt` | [Implemented] |
| Prompt change governance | Prompt edits reviewed before release | [Process/Target] |
| Prompt audit tracking | Posture tracks prompt audits + unsafe-prompt signals | [Implemented/Demo] |
| Injection guardrail | Grounded-only context limits injection blast radius | [Partial] |

## 4. Risk assessment (AI Governance posture — 6 dimensions)

`ecs_ai_governance_drilldowns` scores: **Data Privacy · Model Risk · Prompt Safety · Bias · Audit Trail · Human-in-Loop**, rolled into an **AI Compliance Score** (target ≥90). Each AI use case is assessed on:
- Data classification of inputs (drives local vs cloud).
- Hallucination risk (mitigated by grounding gate + citations).
- Human oversight requirement (human-in-loop dimension).
- Auditability (citations + audit log).

## 5. Monitoring

| Signal | Where | Action |
|---|---|---|
| AI Compliance Score | `/mvp/ai-governance` | below target → remediate weak dimension |
| Hallucination rate | posture | rising → check grounding/index |
| Prompt audits / unsafe-prompt signals | posture | investigate flagged prompts |
| Token usage | posture | cost/anomaly watch |
| RAG readiness | `rag_status()` | vector count vs evidence; provider configured |
| LLM connectivity | `llm_connectivity()` | provider reachable + embed dim |

## 6. Revalidation [Process/Target]

- **Trigger:** model/provider change, prompt change, framework change, periodic cadence.
- **Checks:** re-run grounding/citation/refusal tests; confirm RBAC scoping; re-embed if embedding model changed; verify posture score holds.
- **Cadence (recommended):** quarterly or on any change to `llm.yaml`/`prompt_builder`/`vectorstore.yaml`.

## 7. Retirement [Process]

- Mark the use case retired in AI Registry; disable provider/route as needed.
- Decommission embeddings if the source data is removed (re-index drops orphaned content by hash).
- Retain audit log + citations for the retention period (evidence is source of record).

## 8. RACI (recommended)

| Activity | AI Gov Owner | AI SDLC Owner | Compliance | Platform Eng |
|---|:--:|:--:|:--:|:--:|
| Model/provider approval | A | C | C | R |
| Prompt approval | A | R | C | C |
| Risk assessment | A | C | R | C |
| Monitoring | R | C | C | R |
| Revalidation | A | R | C | R |
| Retirement | A | R | C | R |

---

## 9. Maturity & gaps

| Capability | Status |
|---|---|
| Stage-gated AI delivery (AI SDLC) | [Implemented] |
| Posture scoring (6 dims) | [Implemented] |
| Grounding + citation + refusal | [Implemented] |
| Registry of models/prompts | [Implemented] |
| Automated prompt/model change control | [Target] |
| Automated revalidation + eval harness | [Target] |
| Full prompt/response audit table | [Partial] |

**Cross-links:** [Security Architecture](ECS_AI_SECURITY_ARCHITECTURE.md) · [Functional Requirements](ECS_AI_FUNCTIONAL_REQUIREMENTS.md) · [Architecture Reference](ECS_AI_ARCHITECTURE_REFERENCE.md) · [Completeness Report](ECS_AI_DOCUMENT_COMPLETENESS_REPORT.md)
