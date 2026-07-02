# ECS 16K-input / 1K-output Local Ollama Token Validation Benchmark

A lightweight, **additive** wrapper around the existing Neev validation benchmark. It
runs a **single controlled scenario** so two separate 16 GB RAM machines can check out
this branch and execute the **same** local-Ollama token measurement.

- Script: `scripts/run_16k_1k_token_validation.py`
- Reuses: `scripts/run_neev_validation_benchmark.py` (runner functions + prompt capture),
  `benchmarks/ai_workload/realistic_prompt_factory.py`,
  `benchmarks/ai_workload/realistic_neev_validation_profiles.py`
- No existing benchmark logic, prompt content, or documentation is modified or overwritten.

---

## 1. Purpose

Validate local **Ollama 16K context-window behaviour** and attempt **~1K output token
generation** on 16 GB RAM machines, using a realistic ECS assessment prompt. The result
is a defensible local measurement of input/output token shape for budgeting.

## 2. Scope

Prompt-construction + **LLM-token measurement** benchmark. It builds a realistic ECS
prompt and sends it to the **local Ollama** provider, then records the model-reported
token counts.

## 3. Not in scope

- Live RAG retrieval
- PGVector / vector search
- Embeddings (e.g. `nomic-embed-text`)
- Physical evidence files
- OCR
- Object storage / MinIO

This is **local Ollama token measurement only** — the same scope as the underlying Neev
benchmark (a RAG-informed, prompt-construction benchmark; not an end-to-end live-RAG run).

## 4. Why profile `full` is used

The existing `full` scenario (Single App Full Assessment) constructs a prompt of roughly
**~102,467 characters / ~25,617 estimated input tokens** — larger than a 16K context
window. With `num_ctx=16384`, the local model evaluates **up to the context window**, so
the **MEASURED** input (`prompt_eval_count`) lands around **16K**. That is precisely the
local 16K context behaviour this benchmark is meant to validate. No new prompt framework
is created — an existing profile is reused.

## 5. Why `max_output_tokens=1024`

To check whether the local Ollama model can produce **approximately 1K output tokens**,
which is then used for engineering extrapolation/planning. Output is **measured** from
the model's `eval_count`, not assumed.

## 6. Interpretation rules

- **MEASURED input** = Ollama `prompt_eval_count` (real, model-reported).
- **MEASURED output** = Ollama `eval_count` (real, model-reported).
- A `truncation_suspected = true` flag means the constructed prompt exceeded
  `num_ctx=16384`, so the MEASURED input reflects context-window-limited evaluation
  (this is the expected, validating behaviour for the 16K test).
- **3K output** remains **extrapolated / planning** unless explicitly benchmarked.
- **50K input** remains **enterprise planning** based on the constructed enterprise
  prompt shape (see the `enterprise` / `large_repository_*` profiles), not a single
  measured value from this 16K test.

## 7. Extrapolation explanation (engineering, not measurement)

If this benchmark measures ~**16K input** and ~**1K output**, the planning extrapolation
may be documented as:

- `16K input × ~3 = 48K → rounded to 50K`
- `1K output × ~3 = 3K`

> These multipliers are **engineering extrapolation for planning**, clearly labelled as
> such — **not** a direct measurement. Direct measurement covers only the ~16K input /
> ~1K output actually produced in this run.

## 8. Commands for 16 GB machines

### Git Bash

```bash
ECS_LLM_PROVIDER=ollama \
OLLAMA_URL=http://localhost:11434 \
OLLAMA_MODEL=qwen3:8b \
PYTHONPATH=. \
python -m scripts.run_16k_1k_token_validation
```

### Windows CMD

```bat
set PYTHONPATH=.
set ECS_LLM_PROVIDER=ollama
set OLLAMA_URL=http://localhost:11434
set OLLAMA_MODEL=qwen3:8b
python -m scripts.run_16k_1k_token_validation
```

Prerequisites on the 16 GB machine: Ollama running (`ollama serve`) and the model pulled
(`ollama pull qwen3:8b`). No Docker, Postgres, PGVector, or MinIO is required.

Safe inspection on any machine (no Ollama call):

```bash
PYTHONPATH=. python -m scripts.run_16k_1k_token_validation --dry-run
```

## 9. Where results are written

All under `benchmark_outputs/`:

- `prompts/full.txt` — the exact final prompt sent to the model (captured before the call)
- `prompts/prompt_summary.csv` — per-scenario prompt size + token summary
- `neev_validation_results.csv` — standard per-run result row
- `prompt_composition_report.csv` — per-section prompt composition
- `neev_capacity_projection.csv` — Neev projection for the run
- **`16k_1k_validation_history.md`** — cumulative, **append-only**; one timestamped
  section per run
- **`16k_1k_validation_history.csv`** — cumulative, **append-only**; one row per run

The two `16k_1k_validation_history.*` files are **never overwritten**: each run appends a
new timestamped section (md) and a new row (csv). If they don't exist yet they are created
with a heading / header row.

## 10. CSV history columns

`timestamp, git_commit, scenario, command, provider, model, num_ctx_requested,
max_output_tokens, timeout_seconds, prompt_file, prompt_characters,
estimated_input_tokens, measured_input_tokens, measured_output_tokens,
measured_total_tokens, status, truncation_suspected, error_message`

## 11. Safety properties

- Runs **exactly one** scenario; no loops; exits after a single run.
- Does **not** require Docker or PGVector.
- Default settings are conservative for 16 GB RAM: `num_ctx=16384`,
  `max_output_tokens=1024`, `timeout_seconds=600`, timeout-evidence allowed.
- On timeout/error, output is reported as **NOT measured** (never fabricated).
- Changes no production defaults: the context/output/timeout values are supplied through
  the existing benchmark-only configuration hook for the duration of the run.
