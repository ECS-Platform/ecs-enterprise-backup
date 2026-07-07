# ECS Audit LLM — Local Benchmark Plan (16 GB / 20 GB)

Plan for benchmarking the audit LLM prompts on the two available local laptops
(**16 GB** and **20 GB** — there is no 28 GB machine). Uses
`config/audit_llm_benchmark_profiles.yaml` and
`scripts/run_audit_llm_benchmark.py`; evidence lands in
`reports/audit_llm_benchmarks/`.

---

## 1. Profiles under test

| Profile | Machine | Context | Output | Concurrency | Timeout | top_k | Mode |
|---------|---------|---------|--------|-------------|---------|-------|------|
| `local_16gb_safe` | 16 GB | 8192 (opt 16384) | 1024/2048 | 1 | 180s | 5 | llm |
| `local_20gb_extended` | 20 GB | 16384 (opt 20480) | 2048 | 1 (opt 2) | 240s | 8 | llm |
| `worst_case_enterprise_dry_run` | any | 20000 | — | — | — | — | dry_run |

## 2. Token profiles per machine

| Token profile | 16 GB | 20 GB |
|---------------|-------|-------|
| small_4k | ✅ | ✅ |
| medium_8k | ✅ | ✅ |
| large_16k | ⚠️ selected prompts, concurrency 1 | ✅ |
| extended_20k | ⛔ blocked (do not force) | ⚠️ selected prompts |
| worst_case_enterprise_dry_run | dry-run only | dry-run only |

## 3. Run matrix

### Phase 0 — Prompt library validation (any machine, no LLM)
```bash
PYTHONPATH=. pytest tests/test_audit_llm_workbench.py -q
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile worst_case_enterprise_dry_run --all --dry-run
```

### Phase 1 — 16 GB (dry-run first, then LLM)
```bash
# Dry-run (token estimates only — no model load):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --all --dry-run

# 4K/8K LLM runs (concurrency 1):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --category observations --execute
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --category executive --execute

# Selected 16K prompts ONLY (concurrency 1):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --prompt csite_closure_probability \
  --token-profile large_16k --execute
```
Do **not** run `extended_20k` on 16 GB (it is blocked in the profile).

### Phase 2 — 20 GB
```bash
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_20gb_extended --all --dry-run
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_20gb_extended --category analytics --execute
# Selected 20K prompts (after a stable baseline):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_20gb_extended --prompt compliance_trend_forecast \
  --token-profile extended_20k --execute
```

## 4. What each report captures

Each report (Markdown + JSON in `reports/audit_llm_benchmarks/`) records, per
prompt: timestamp, machine profile, RAM profile, provider, model, prompt_id,
category, query_type, token profile, estimated input/output/total tokens, latency,
success/failure, fallback used, memory warning, deterministic result count, LLM
response quality notes, reproducibility notes.

## 5. Pass / fail criteria

| Check | Pass |
|-------|------|
| Dry-run (all prompts) | 40/40 produce a token estimate; no crash |
| 16 GB 4K/8K LLM | prompts complete within timeout; no OOM/swap thrash |
| 16 GB 16K (selected) | selected prompts complete concurrency 1; memory stable |
| 20 GB 16K | prompts complete; no swap pressure |
| 20 GB 20K (selected) | selected prompts complete; monitor swap; stop if pressure rises |
| Fallback | LLM-unavailable run returns deterministic result, `fallback_used=true` |

## 6. Capture template (per run)

```
model: <name>            provider: <ollama|...>   machine RAM: <16|20> GB
ram_profile: <...>       prompt_id: <...>         token_profile: <...>
latency: <ms>            success: <yes|no>        fallback_used: <yes|no>
memory_warning: <...>    qualitative_notes: <...>
```

## 7. Reproducibility

Benchmark samples are fixed per `prompt_id` and token estimates are deterministic
(chars/4), so dry-run reports are byte-stable across machines. LLM latency/quality
vary by model + RAM and are recorded as observed.
