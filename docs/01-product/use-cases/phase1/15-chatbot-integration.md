# Chatbot Integration

## Purpose

Answer common evidence questions deterministically from persisted repository data (and selected RAG paths) without requiring users to navigate every module—while refusing unsupported claims when evidence is absent.

## Business problem solved

Auditors and owners ask repeated questions (“latest evidence for control X”, “open observations”, “failed collections”). The chatbot routes known intents to authoritative data instead of hallucinating.

## Phase-1 scope

- **In scope:** Deterministic preset handlers (`common_evidence_presets`); hybrid query router (`common_evidence_queries`); citations with evidence_id; RBAC application scope; integration with search/authoritative reader; AI Ops Assistant UI; optional RAG for free-text when configured.
- **Out of scope:** Replacing LLM provider architecture; autonomous remediation actions.

## High-level workflow

```
User question (UI chat or /chat API)
  → try_deterministic_evidence_query (pattern + presets)
  → If match: collect_persisted_evidence_rows → scoped filter → structured answer + citations
  → Else: try_rag_evidence_query (PGVector + provider) with grounding/refusal rules
  → Return answer_source DETERMINISTIC | RAG | no_evidence
```

## Existing implementation (reuse current code)

| Area | Module / service |
|------|------------------|
| Presets | `modules/shared/services/common_evidence_presets.py` |
| Query router | `modules/shared/services/common_evidence_queries.py` |
| Chat entry | `app.main.chatbot_answer` |
| RAG | `ecs_platform/rag.py` (when LLM configured) |
| UI | `modules/shared/routes/routes_mvp` AI Ops Assistant |

## Existing APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/chat` | Chatbot answer |
| GET | `/api/platform/assistant` | Assistant query (governance routes) |
| GET | `/mvp/ai-ops-assistant` | Chat UI |

## Existing UI pages

| Page | Route |
|------|-------|
| AI Ops Assistant | `/mvp/ai-ops-assistant` |

## Existing tests

- `tests/test_common_evidence_chatbot.py`
- `tests/test_common_evidence_presets.py`
- `tests/test_phase1_e2e_lifecycle_validation.py` (chatbot absence + preset rows)
- `tests/test_rag_answer_validation.py`

## Demo scenario

1. Persist **PGX-001** evidence.
2. Ask: “Show latest evidence for control PGX-001 in Net Banking” — answer cites correct `evidence_id`.
3. Run preset **Last 5 evidences** — lists scheduler and upload sources.
4. Ask about **ZZZ-999** — returns no-evidence message, no fabricated citation.
5. After certificate-management FAIL collection, **Last 5 evidences** or observation presets surface FAIL metadata / open observations where seeded.

## Known Phase-1 limitations

- Not all natural-language phrasings map to deterministic handlers; free-text falls back to RAG or generic responses.
- RAG requires configured embedding/LLM provider; demo often uses deterministic path only.
- `source_type` display may show lowercase `predefined_query` vs legacy `PREDEFINED_QUERY` in some RAG citation tests.
