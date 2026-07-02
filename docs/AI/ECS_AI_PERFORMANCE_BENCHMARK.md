# ECS AI Performance Benchmark (Phase 10)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

> **Integrity notice.** This assessment is documentation-only and runs in an environment where no
> local models are installed and no benchmark harness was executed. The tables below are therefore
> presented as **(a) a reproducible benchmark methodology** and **(b) reference-range expectations**
> drawn from each model's published characteristics and the ECS integration contract — **not** as
> measured ECS results. Real numbers must be captured in the target environment using the harness in
> §2. No fabricated "measured" values are presented as fact.

---

## 1. What to benchmark (ECS-specific)

ECS only exercises two model operations (`provider.generate`, `provider.embed`), so the benchmark
targets those over real ECS payloads:

| Workload | ECS path | Metric(s) |
|---|---|---|
| RAG answer generation | `rag.py:649` `provider.generate()` | latency (P50/P95), tokens/sec, answer quality |
| Embedding (index + query) | `provider.embed()` → pgvector | embed latency/doc, index throughput, recall@k |
| End-to-end assistant | `/api/platform/assistant` | wall-clock, grounded-rate |

---

## 2. Reproducible benchmark harness (to run in target env)

```bash
# 1. Pull models
ollama pull qwen3:8b llama3:8b deepseek-r1:7b mistral gemma2:9b nomic-embed-text

# 2. For each model, set config and warm
export ECS_LLM_PROVIDER=ollama ECS_LLM_MODEL=<model> OLLAMA_URL=http://<host>:11434

# 3. Generation latency/throughput (direct Ollama, ECS-equivalent payload)
curl -s http://<host>:11434/api/chat -d '{"model":"<model>","messages":[{"role":"user","content":"<ECS governance prompt>"}],"stream":false}' \
  | jq '{total_ms:(.total_duration/1e6), eval_count, tok_per_s:(.eval_count/(.eval_duration/1e9))}'

# 4. ECS end-to-end (grounded RAG)
curl -s http://<ecs>/api/platform/assistant -d '{"question":"Which controls have rejected evidence in PCI DSS?"}' | jq '.mode,.grounded'

# 5. Embeddings throughput
curl -s http://<host>:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"<chunk>"}' | jq '.embedding|length'
```

Capture: response time (P50/P95), tokens/sec, peak RAM (`nvidia-smi` / `htop`), CPU%, and a blind
quality rubric (faithfulness, completeness, hallucination) scored by a reviewer on 20 ECS prompts.

---

## 3. Reference expectation ranges (NOT measured ECS results)

CPU-only and single mid-range GPU are both shown because banking on-prem nodes vary widely. Ranges are
order-of-magnitude planning guidance only.

| Model | Params | Tokens/sec (1×mid GPU, ref) | Tokens/sec (CPU, ref) | Peak RAM (Q4, ref) | Quality (ref) |
|---|---|---|---|---|---|
| Qwen3 8B | 8B | ~40–80 | ~6–15 | ~6–8 GB | High |
| Llama3 8B | 8B | ~45–90 | ~7–16 | ~6–8 GB | High |
| DeepSeek-R1 7B | 7B | ~35–70 (verbose) | ~5–12 | ~6–9 GB | High reasoning |
| Mistral 7B | 7B | ~50–95 | ~8–18 | ~5–7 GB | Good |
| Gemma2 9B | 9B | ~35–70 | ~5–12 | ~7–9 GB | Good–High |
| *Cloud baseline (OpenAI/Gemini)* | — | network-bound | n/a | n/a | High (but egress/data-residency cost) |

Embedding reference: `nomic-embed-text` ~hundreds of chunks/sec on GPU, tens/sec on CPU; 768-dim.

---

## 4. Cloud vs local trade-off (qualitative, decision-grade)

| Dimension | Local (Ollama) | Cloud (OpenAI/Gemini/Anthropic/Azure) |
|---|---|---|
| Data residency / air-gap | ✅ Full control | ❌ Egress required (Azure OpenAI = private-ish) |
| Latency | Predictable, no WAN | WAN-dependent |
| Cost model | Fixed (hardware) | Per-token |
| Quality ceiling | High (8–14B), very high w/ GPU & larger models | Highest |
| Banking compliance | ✅ Best fit | Requires DPA/residency review |

For banking audit/governance/compliance/risk data, **local is the recommended default**; cloud is an
opt-in for non-sensitive, non-air-gapped environments.

---

## 5. Conclusion

ECS's two model operations make benchmarking tractable and bounded. Run §2 in the target environment
to replace §3's reference ranges with real numbers before production sign-off. Expected outcome:
8–9B local models (qwen3:8b default) deliver production-acceptable latency/quality on a single GPU and
usable performance on CPU for UAT/demo.
