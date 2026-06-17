# ECS Local LLM Deployment & Installation Guide (Phase 2)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`
**Scope:** Documentation only. Commands reference real ECS config keys (`config/llm.yaml`,
`config/vectorstore.yaml`, `docker-compose.yml`).

ECS local LLM needs exactly two external services on the private network:
1. **Ollama** (serves the chat + embedding models) — `OllamaProvider` (`provider.py:157-227`)
2. **Postgres + pgvector** (vector store) — `pgvector_store.py`, `docker-compose.yml:144-153`

No cloud account or API key is required.

---

## 0. Configuration keys (all environments)

| Variable | Default | Source |
|---|---|---|
| `ECS_LLM_PROVIDER` | `ollama` | `config/llm.yaml:7` |
| `ECS_LLM_MODEL` | `qwen3:8b` | `config/llm.yaml:8` |
| `ECS_EMBEDDING_MODEL` | `nomic-embed-text` | `config/llm.yaml:9` |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | `config/llm.yaml:20`, `docker-compose.yml:70` |
| `OLLAMA_MODEL` | `qwen3:8b` | `docker-compose.yml:71` |
| `ECS_OLLAMA_KEEP_ALIVE` | `30m` | `config/llm.yaml:14` |
| `ECS_VECTOR_PROVIDER` | `pgvector` | `config/vectorstore.yaml:4` |
| `ECS_VECTOR_DIM` | `768` | `config/vectorstore.yaml:5` |

---

## 1. macOS (developer workstation)

```bash
# Ollama
brew install ollama          # or download from ollama.com
ollama serve                 # starts daemon on :11434

# Models
ollama pull qwen3:8b
ollama pull nomic-embed-text
# optional alternatives
ollama pull llama3
ollama pull mistral
ollama pull phi3
ollama pull deepseek-r1
ollama pull gemma2:9b

# pgvector (via docker compose already in repo)
docker compose up -d pgvector       # service in docker-compose.yml:144-153

# Point ECS at local services
export ECS_LLM_PROVIDER=ollama ECS_LLM_MODEL=qwen3:8b \
       ECS_EMBEDDING_MODEL=nomic-embed-text OLLAMA_URL=http://localhost:11434 \
       ECS_VECTOR_DIM=768
```

## 2. Windows

```powershell
# Ollama — install the Windows package from ollama.com (runs as a service on :11434)
ollama pull qwen3:8b
ollama pull nomic-embed-text

# pgvector — use Docker Desktop
docker compose up -d pgvector

# Environment (PowerShell)
$env:ECS_LLM_PROVIDER="ollama"; $env:ECS_LLM_MODEL="qwen3:8b"
$env:ECS_EMBEDDING_MODEL="nomic-embed-text"; $env:OLLAMA_URL="http://localhost:11434"
$env:ECS_VECTOR_DIM="768"
```

> Dockerized ECS reaching host Ollama uses `OLLAMA_URL=http://host.docker.internal:11434` (the repo
> default), which works on Docker Desktop for Mac/Windows.

## 3. Linux (server / on-prem node)

```bash
# Ollama
curl -fsSL https://ollama.com/install.sh | sh     # online install
sudo systemctl enable --now ollama                # daemon on :11434

ollama pull qwen3:8b
ollama pull nomic-embed-text

# pgvector
docker compose up -d pgvector
# or native: install postgresql + CREATE EXTENSION vector;

export ECS_LLM_PROVIDER=ollama ECS_LLM_MODEL=qwen3:8b \
       ECS_EMBEDDING_MODEL=nomic-embed-text OLLAMA_URL=http://127.0.0.1:11434 \
       ECS_VECTOR_DIM=768
```

### Air-gapped Linux (no internet)

```bash
# On an internet-connected staging box, pull models then export the blob store:
ollama pull qwen3:8b && ollama pull nomic-embed-text
tar czf ollama-models.tgz -C ~/.ollama models    # vendor the blobs

# Transfer ollama-models.tgz + ollama binary + pgvector image to the air-gapped host, then:
tar xzf ollama-models.tgz -C ~/.ollama
docker load -i pgvector-pg16.tar                  # pre-saved image
```

## 4. UAT

| Item | Recommendation |
|---|---|
| Ollama | Single GPU node (or strong CPU node), `ECS_OLLAMA_KEEP_ALIVE=30m` |
| Models | `qwen3:8b` + `nomic-embed-text` (validate alternatives per Compatibility doc) |
| pgvector | Dedicated Postgres with `vector` extension, `ECS_VECTOR_DIM=768` |
| Config | `ECS_LLM_PROVIDER=ollama` |
| Validation | Run the Testing Guide functional + RAG + vector suites |
| Warm-up | `POST /api/platform/rag/warm` after deploy (`routes_governance.py:349-357`) |

## 5. Production (air-gapped / on-prem)

| Concern | Action |
|---|---|
| Provider lock | Force `ECS_LLM_PROVIDER=ollama`; block AI egress at network policy |
| Models | Vendored blobs, pinned digests; `qwen3:8b` + `nomic-embed-text` (+ quality tier if approved) |
| Capacity | Size GPU node per Phase 10 benchmark; keep-alive warm |
| pgvector | HA Postgres; `ECS_VECTOR_DIM` must match embedding model |
| Resilience | Deterministic fallback verified (stop Ollama → assistant still answers via `governance_qa`) |
| Health | `GET /api/platform/rag/status` + `/llm` in readiness probes; alert on fallback mode |
| Reindex | `POST /api/platform/rag/reindex` (admin) after evidence load (`routes_governance.py:359-367`) |

---

## 6. Validation commands (all environments)

```bash
# Ollama up + models present
curl -s http://localhost:11434/api/tags | jq '.models[].name'

# Generation smoke test (ECS-equivalent payload)
curl -s http://localhost:11434/api/chat \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"ping"}],"stream":false}' | jq '.message.content'

# Embedding smoke test (dimension should equal ECS_VECTOR_DIM)
curl -s http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"control evidence"}' | jq '.embedding | length'

# ECS RAG status / connectivity
curl -s http://<ecs-host>/api/platform/rag/status | jq
curl -s http://<ecs-host>/api/platform/rag/llm    | jq

# End-to-end grounded answer (expect mode=rag, grounded=true)
curl -s "http://<ecs-host>/api/platform/assistant?q=Which%20controls%20have%20rejected%20evidence%20in%20PCI%20DSS" | jq '.mode,.grounded'
```

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Assistant returns `mode: fallback` | Provider not configured / Ollama unreachable | Check `OLLAMA_URL`, `ollama serve`, `/api/platform/rag/status` |
| `Ollama embeddings returned empty vector` | Wrong/missing embedding model | `ollama pull nomic-embed-text`; set `ECS_EMBEDDING_MODEL` |
| pgvector search returns nothing | Index empty or dimension mismatch | Run reindex; ensure `ECS_VECTOR_DIM` matches model dim |
| Cosine search errors after model swap | Dimension changed (e.g. bge-large=1024) | Recreate `evidence_embeddings` at new dim + full reindex |
| First query very slow | Cold start | `POST /api/platform/rag/warm`; raise `ECS_OLLAMA_KEEP_ALIVE` |
| Docker ECS can't reach host Ollama | URL points at localhost inside container | Use `OLLAMA_URL=http://host.docker.internal:11434` |
| Accidental cloud calls | `ECS_LLM_PROVIDER` not `ollama` | Lock to `ollama` in prod; verify env |

> Error strings above are real: empty-vector (`provider.py:204`), Ollama response check
> (`provider.py:191-192`). Fallback logging at app startup: `app/main.py:150-168`.
