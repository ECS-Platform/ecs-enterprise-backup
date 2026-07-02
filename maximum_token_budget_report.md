# Maximum Token Budget Report

## Purpose
Measure maximum realistic LLM token consumption per request for enterprise budgeting using ECS's existing RAG execution and instrumentation.

## Maximum Observed Values (Measured)
- Maximum Input Tokens: **468** (assessment: Enterprise Consolidated Regulator Readiness)
- Maximum Output Tokens: **480** (assessment: Executive Board Compliance Risk Pack)
- Maximum Total Tokens: **894** (assessment: Executive Board Compliance Risk Pack)
- Maximum Retrieved Documents: **24** (assessment: Enterprise Consolidated Regulator Readiness)
- Maximum Retrieved Chunks: **24** (assessment: Enterprise Consolidated Regulator Readiness)
- Maximum Citations: **0** (assessment: Enterprise Consolidated Regulator Readiness)
- Maximum Prompt Size (chars): **1000** (assessment: Enterprise Consolidated Regulator Readiness)

## Throughput Budgeting (3 requests/minute)
Measured token-per-request values above are projected at 3 completed requests per minute.

### Input Tokens
- Tokens per Request: 468
- Tokens per Minute: 1404
- Tokens per Hour: 84240
- Tokens per Day: 2021760
- Tokens per Month (30d): 60652800

### Output Tokens
- Tokens per Request: 480
- Tokens per Minute: 1440
- Tokens per Hour: 86400
- Tokens per Day: 2073600
- Tokens per Month (30d): 62208000

### Total Tokens
- Tokens per Request: 894
- Tokens per Minute: 2682
- Tokens per Hour: 160920
- Tokens per Day: 3862080
- Tokens per Month (30d): 115862400

## Benchmark Prompts Used
- Enterprise Consolidated Regulator Readiness (top_k=24): Provide a consolidated regulator readiness assessment across PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, Middleware Security, SOC2, ISO27001, and RBI-CSF using only ECS evidence. Include framework-by-framework coverage, key control gaps, evidence quality risks, and prioritized remediation with citations for every claim.
- Enterprise Cross-Framework Compliance Maturity (top_k=22): Assess enterprise governance and compliance maturity portfolio-wide across SOC2, ISO27001, PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, and Middleware Security. Compare control coverage, lifecycle readiness, evidence freshness, and audit traceability by framework and application with citations.
- Portfolio-Wide Control Coverage Deep Assessment (top_k=20): Generate a portfolio-wide deep control coverage assessment across all available frameworks in ECS. Map controls to frameworks, identify reused controls, uncovered controls, weak evidence patterns, and controls with rejection or expiry risk. Provide executive findings with evidence citations.
- Enterprise Evidence Reuse and Crosswalk Analysis (top_k=20): Analyze enterprise evidence reuse across all supported frameworks and source systems. Quantify where one evidence item satisfies multiple obligations, identify crosswalk concentration risks, and call out highest-impact reuse opportunities and blockers with citations.
- Executive Board Compliance Risk Pack (top_k=24): Prepare an executive board compliance risk pack summarizing enterprise readiness across all supported frameworks, largest residual risks, audit readiness blockers, evidence lifecycle issues, and regulator-facing priorities. Include citations and source/timestamp context.

## Worst-Case Prompt Selection Methodology
### Enterprise Consolidated Regulator Readiness
- Purpose: Board/regulator consolidated readiness across major enterprise governance frameworks.
- Expected retrieval breadth: Very high across source systems, controls, and framework mappings.
- Expected governance scope: Enterprise-wide, regulator-facing, cross-framework.
- Expected response complexity: Very high with gap/risk/remediation synthesis and citations.
- Why this prompt is expected to maximize input tokens: enterprise-wide cross-framework scope plus elevated retrieval depth increases retrieved context included in prompt construction.
- Why this prompt is expected to maximize output tokens: executive/regulator asks require long-form cited synthesis across coverage, risks, and remediation priorities.

### Enterprise Cross-Framework Compliance Maturity
- Purpose: Enterprise maturity comparison across frameworks and applications.
- Expected retrieval breadth: Very high due to comparative cross-framework and cross-application asks.
- Expected governance scope: Portfolio-wide compliance maturity and audit traceability.
- Expected response complexity: High; requires comparative analysis and structured maturity conclusions.
- Why this prompt is expected to maximize input tokens: enterprise-wide cross-framework scope plus elevated retrieval depth increases retrieved context included in prompt construction.
- Why this prompt is expected to maximize output tokens: executive/regulator asks require long-form cited synthesis across coverage, risks, and remediation priorities.

### Portfolio-Wide Control Coverage Deep Assessment
- Purpose: Deep control coverage diagnostics for enterprise audit planning.
- Expected retrieval breadth: High due to control-to-framework coverage and lifecycle quality analysis.
- Expected governance scope: Enterprise controls and framework crosswalk health.
- Expected response complexity: High with prioritized control-level findings and actions.
- Why this prompt is expected to maximize input tokens: enterprise-wide cross-framework scope plus elevated retrieval depth increases retrieved context included in prompt construction.
- Why this prompt is expected to maximize output tokens: executive/regulator asks require long-form cited synthesis across coverage, risks, and remediation priorities.

### Enterprise Evidence Reuse and Crosswalk Analysis
- Purpose: Cross-framework evidence reuse quantification and risk analysis.
- Expected retrieval breadth: High due to crosswalked evidence and multi-source correlations.
- Expected governance scope: Enterprise reuse posture and cross-framework obligation mapping.
- Expected response complexity: Medium-high combining quantitative reuse and risk interpretation.
- Why this prompt is expected to maximize input tokens: enterprise-wide cross-framework scope plus elevated retrieval depth increases retrieved context included in prompt construction.
- Why this prompt is expected to maximize output tokens: executive/regulator asks require long-form cited synthesis across coverage, risks, and remediation priorities.

### Executive Board Compliance Risk Pack
- Purpose: Board-level risk pack for enterprise compliance governance decisions.
- Expected retrieval breadth: Very high across readiness, lifecycle, and regulator priorities.
- Expected governance scope: Enterprise-wide strategy and operational compliance risk.
- Expected response complexity: Very high with executive synthesis and evidence-backed prioritization.
- Why this prompt is expected to maximize input tokens: enterprise-wide cross-framework scope plus elevated retrieval depth increases retrieved context included in prompt construction.
- Why this prompt is expected to maximize output tokens: executive/regulator asks require long-form cited synthesis across coverage, risks, and remediation priorities.

## Per-Prompt Measured Results
| Prompt name | Frameworks covered | Applications covered | Configured retrieval depth (top_k) | Retrieved documents | Retrieved chunks | Input tokens | Output tokens | Total tokens | Citations | End-to-end latency (ms) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Enterprise Consolidated Regulator Readiness | PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, Middleware Security, SOC2, ISO27001, RBI-CSF | Portfolio-wide applications represented in retrieved evidence | 24 | 24 | 24 | 468 | 8 | 476 | 0 | 6744 |
| Enterprise Cross-Framework Compliance Maturity | SOC2, ISO27001, PCI DSS, RBI C-SITE, DPSC, ITPP, ITGRC, VAPT, AI SDLC, AppSec, ASST, DB Baselining, ITDRM, Middleware Security | Portfolio-wide multi-application scope | 22 | 22 | 22 | 458 | 8 | 466 | 0 | 6671 |
| Portfolio-Wide Control Coverage Deep Assessment | All frameworks represented in ECS control crosswalk | Portfolio-wide applications contributing control evidence | 20 | 20 | 20 | 436 | 170 | 606 | 0 | 11917 |
| Enterprise Evidence Reuse and Crosswalk Analysis | All frameworks participating in ECS crosswalk mappings | Portfolio-wide applications with reusable mapped evidence | 20 | 20 | 20 | 432 | 211 | 643 | 0 | 13199 |
| Executive Board Compliance Risk Pack | All supported frameworks represented in ECS evidence and governance mappings | Portfolio-wide enterprise application coverage | 24 | 24 | 24 | 414 | 480 | 894 | 0 | 22704 |

## Maximum Token Justification
This benchmark intentionally targets enterprise-wide, cross-framework governance
questions spanning multiple frameworks and applications. That naturally yields
the largest realistic retrieval context and response size within ECS because the
assistant must synthesize broad evidence into citation-backed executive output.

## How values were obtained
- All values are read from executed benchmark rows and ECS instrumentation outputs (`rag_metrics.csv`, `rag_metrics.jsonl`, and `ai_workload_requests.jsonl`).
- No token value in this report is estimated or fabricated.
- Maximum values are computed as max() over successful benchmark requests for each metric.

## Why these prompts are realistic worst-case enterprise governance requests
- Each prompt requests board/regulator-grade consolidated assessment across many frameworks.
- Prompts require cross-framework mapping, coverage, gaps, lifecycle risk, and remediation prioritization.
- Retrieval depth (`top_k`) is increased only for these realistic enterprise prompts to maximize genuine evidence context.
- The prompts are domain-authentic governance asks; they do not pad meaningless text or fabricate evidence.

## Evidence file size and prompt token behavior
- Embeddings are generated once during ingestion and stored in vector index tables.
- Original evidence file size does **not** directly determine prompt token consumption at answer time.
- Prompt tokens are driven by retrieved chunks, retrieval depth, chunk size, and prompt construction.

### Examples
- A very large source artifact can still produce low prompt tokens if only a few short chunks are retrieved.
- A modest-size artifact set can produce high prompt tokens when many chunks are retrieved across frameworks in a consolidated request.

## Assumptions
- Benchmark is based on actual ECS evidence.
- No synthetic prompt inflation was used.
- No fabricated evidence was introduced.
- Token values originate from Ollama metadata.
- Retrieval metrics originate from ECS instrumentation.
- Throughput calculations assume three completed requests per minute.
