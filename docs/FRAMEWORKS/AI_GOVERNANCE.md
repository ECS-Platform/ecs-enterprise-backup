# Framework Reference — AI Governance

**Grounding:** AI Governance posture (`ecs_ai_governance_drilldowns`, 6 dimensions), AI-SDLC stage gates (`ai_sdlc_governance_service`), `docs/AI/*`. Route `/mvp/ai-governance`, `/mvp/ai-sdlc`. **Status:** Implemented as a governance **posture + stage-gate model** (not a `FRAMEWORK_CATALOG` control set). Part of [Frameworks Library](README.md).

## Purpose
Govern AI/LLM usage in ECS and AI-enabled banking delivery — risk, safety, auditability, human oversight.

## Objectives (6 posture dimensions)
Data Privacy · Model Risk · Prompt Safety · Bias/Fairness · Audit Trail · Human-in-the-Loop. Plus AI-SDLC stage gates (Requirements → Design → Build → Test → Go-Live).

## Controls / Gates
Per-dimension posture controls (weighted to AI Compliance Score) + AI-SDLC evidence-backed stage gates. Anti-hallucination guardrails: `require_citations`, `refuse_without_evidence` (`config/llm.yaml`).

## Checklist (sample)
- [ ] AI use case registered (AI Registry)
- [ ] Prompt reviewed/approved
- [ ] RBAC scope applied before model call
- [ ] Citations required; refusal without evidence
- [ ] Audit log of AI interactions
- [ ] Human review on AI outputs

## Evidence Requirements
Model/prompt registry entries, governance posture exports, AI-SDLC stage evidence, audit logs.

## Control & Evidence Reuse
Audit-trail/access controls reuse with **ISO27001, RBI Cyber, ISG**.

## Reporting / Sample
- **Executive:** AI Compliance Score to board.
- **Audit:** AI governance + AI-SDLC reports (6 reports).
- **Risk:** hallucination rate, open AI findings to Risk Register.
- **Detail:** see [docs/AI/](../AI/README.md) — Governance Operating Model, Security Architecture, Architecture Reference.
