# ECS Audit LLM — 16 GB / 20 GB Local Testing Guide

How to test the audit LLM prompt workbench on the two available local laptops.
**There is no 28 GB machine** — only **16 GB** and **20 GB**. A dry-run profile
supports worst-case enterprise prompts via token estimation with no LLM.

> Profiles: `config/audit_llm_benchmark_profiles.yaml`. Runner:
> `scripts/run_audit_llm_benchmark.py`. Provider/model: `config/llm.yaml`
> (local Ollama by default). Plan: [audit_llm_local_benchmark_plan.md](audit_llm_local_benchmark_plan.md).

---

## 1. Prerequisites (both machines)

- ECS checked out; Python env installed (see `docs/DEVELOPER_SETUP_GUIDE.md`).
- For LLM execution: a local provider running (e.g. Ollama) with a model pulled;
  configured via `config/llm.yaml` / env (`ECS_LLM_PROVIDER`, `ECS_LLM_MODEL`,
  `OLLAMA_URL`). **Nothing is hardcoded** — pick the model your RAM supports.
- No provider needed for **dry-run** or the prompt-library tests.

```bash
export DEMO_MODE=true ECS_AUTH_ENABLED=false ECS_VALIDATE_CONFIG=off
# (LLM) example — model name is your choice, resolved from config/env:
# export ECS_LLM_PROVIDER=ollama ECS_LLM_MODEL=<a-model-your-RAM-supports>
```

---

## 2. On the 16 GB laptop

**Use for:** prompt-library validation, 4K prompt testing, 8K prompt testing,
selected 16K dry-run or low-load testing, concurrency 1, low-memory-pressure runs.

**Avoid:** running a large local model **plus** a heavy Docker stack; 20K prompt
execution (blocked); concurrency above 1.

```bash
# 1. Validate the library + pipeline (no LLM):
PYTHONPATH=. pytest tests/test_audit_llm_workbench.py -q

# 2. Dry-run all prompts (token estimates only, no model load):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --all --dry-run

# 3. 4K/8K LLM runs (concurrency 1, small/medium model):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --category observations --execute

# 4. Selected 16K prompt only (concurrency 1):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_16gb_safe --prompt csite_closure_probability \
  --token-profile large_16k --execute
```

Memory guidance (from the profile): *avoid running a heavy Docker stack and a large
local model at the same time; keep concurrency at 1; prefer small/medium models for
16K prompts.* The token estimator will WARN (and the profile BLOCKS) if you point a
16 GB run at `extended_20k`.

---

## 3. On the 20 GB laptop

**Use for:** 4K/8K/16K prompt testing, selected 20K prompt testing, concurrency 1
(optional concurrency 2 only after a stable baseline), benchmark evidence
generation.

```bash
# Dry-run all prompts:
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_20gb_extended --all --dry-run

# 16K LLM runs:
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_20gb_extended --category analytics --execute

# Selected 20K prompt (after a stable single-thread baseline):
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile local_20gb_extended --prompt compliance_trend_forecast \
  --token-profile extended_20k --execute
```

Memory guidance (from the profile): *monitor swap and stop if memory pressure
increases; use concurrency 1, raise to 2 only after a stable baseline; prefer
medium models.*

---

## 4. Worst-case enterprise (any machine, dry-run only)

```bash
PYTHONPATH=. python scripts/run_audit_llm_benchmark.py \
  --ram-profile worst_case_enterprise_dry_run --all --dry-run
```
Builds the prompt + estimates tokens with **no LLM call, no model load, no
Docker** — safe even on an 8 GB machine. Output: token estimate + assembled-prompt
metadata + warnings.

---

## 5. For both machines — capture

For every LLM run, record:

- model name, provider, machine RAM profile
- prompt id, token profile
- latency, success/failure, fallback used
- memory warning (swap pressure, OOM)
- qualitative output notes (accuracy, hallucination, citation quality)

The runner writes these to `reports/audit_llm_benchmarks/*.md` + `*.json`
automatically; add qualitative notes after reviewing responses.

---

## 6. Using the Workbench UI

Open `/mvp/audit/llm-workbench` (Audit Intelligence → LLM Prompt Workbench). Select
a **RAM profile** and **token profile**, enter a query, and use **Classify /
Estimate tokens / Run prompt / Run benchmark / Export benchmark**. In demo/dry-run
the UI shows the deterministic result and token metrics without calling the LLM;
with a configured local provider it also shows the LLM response, confidence,
assumptions, limitations, and source references.

---

## 7. Fallback behaviour

If the local LLM is not running, **Run prompt** still returns the deterministic
result plus a `[FALLBACK]` message (`fallback_used=true`) — it never errors. Start
your local provider to get the LLM-generated summary/analysis.
