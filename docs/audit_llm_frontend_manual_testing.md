# ECS Audit LLM — Frontend Manual Testing

Manual frontend test cases for the **Audit LLM Prompt Workbench**
(`/mvp/audit/llm-workbench`; nav: Audit Intelligence → LLM Prompt Workbench).

**Common setup for all cases**
- Start ECS: `PYTHONPATH=. uvicorn app.main:app --port 8000` (or `./start_ecs.sh`).
- Open `http://127.0.0.1:8000/mvp/audit/llm-workbench?role=owner&user=U`.
- LLM is optional: with no local provider, **Run prompt** returns the deterministic
  result + a `[FALLBACK]` message (this is expected and testable).
- Screen for all cases: **Audit LLM Prompt Workbench**. URL as above.

**Pass/fail shorthand**
- *Deterministic result* panel shows a sentence + counts.
- *LLM response* panel shows text (live) or `[FALLBACK]` (no provider) or empty
  (dry-run). *Query type*, *Tokens*, *Latency*, *Provider*, *Fallback* update.

---

### TC1 — Open observation count query
- **Prerequisites:** none. **Sample input:** query = "How many observations are open in Net Banking?"; Application = Net Banking. **RAM profile:** local_16gb_safe. **Token profile:** small_4k.
- **Steps:** enter query → (optional) pick prompt `observation_count` → Classify → Run prompt.
- **Expected deterministic:** "There are N open observation(s) for Net Banking." (N ≥ 0).
- **Expected LLM:** short summary of the count (live) / `[FALLBACK]` (no provider).
- **Expected fallback:** deterministic result still shown; Fallback = yes.
- **Pass:** query_type = deterministic; count is an integer; no error.

### TC2 — High-risk observations across all frameworks
- **Sample input:** "How many high-risk observations are open across all frameworks, and summarize the business impact?" **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected deterministic:** "N open high-risk observation(s) across all frameworks." + by_framework.
- **Expected LLM:** 3–5 impact bullets (live) / fallback.
- **Pass:** query_type = hybrid; deterministic count present.

### TC3 — Net Banking C-SITE prediction query
- **Sample input:** "What are the chances my C-SITE observations will not be raised on Net Banking this year?" App = Net Banking; Framework = C-SITE. **RAM:** local_20gb_extended. **Token:** large_16k.
- **Expected deterministic:** closure/observation figures.
- **Expected LLM:** prediction **with confidence, assumptions, limitations** (never stated as certainty).
- **Pass:** query_type = llm_assisted; Confidence/Assumptions/Limitations populated.

### TC4 — Observation aging query
- **Sample input:** "Which high-risk observations are older than 90 days?" Date range = 90 days. **RAM:** local_16gb_safe. **Token:** small_4k.
- **Expected deterministic:** "N observation(s) are older than 90 days." with rows carrying age_days.
- **Pass:** query_type = deterministic; rows bounded; no error.

### TC5 — Evidence gap query
- **Sample input:** "What evidence is missing for PCI DSS readiness?" Framework = PCI DSS. **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected deterministic:** gap count + highest-gap framework.
- **Pass:** deterministic result present; source references shown.

### TC6 — Executive compliance summary
- **Prompt:** executive_compliance_summary. **Sample input:** "Generate an executive summary of current audit readiness." **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected LLM:** executive summary (live) / fallback. **Pass:** query_type = hybrid.

### TC7 — Application owner response drafting
- **Prompt:** application_owner_response. **Sample input:** App = Net Banking; Control = e.g. PCI-10.6; query = "Draft an application owner response for this audit query." **RAM:** local_20gb_extended. **Token:** medium_8k.
- **Expected LLM:** professional draft with assumptions. **Pass:** llm_assisted; assumptions shown; fallback safe.

### TC8 — Closure justification drafting
- **Prompt:** observation_closure_justification. **Sample input:** App = Net Banking; Control set. **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected LLM:** closure justification citing evidence where available. **Pass:** llm_assisted; no crash.

### TC9 — Cross-application readiness comparison
- **Prompt:** cross_application_comparison. **Sample input:** "Compare audit readiness across applications." **RAM:** local_20gb_extended. **Token:** large_16k.
- **Expected deterministic:** open observations by application + least-ready app. **Pass:** hybrid; matrix present.

### TC10 — National dashboard summary
- **Prompt:** pan_india_dashboard_summary. **RAM:** worst_case_enterprise_dry_run. **Token:** worst_case_enterprise_dry_run.
- **Expected LLM:** none (dry-run) — token estimate + assembled prompt only. **Pass:** execution mode dry_run; Fallback = yes; no LLM call.

### TC11 — Evidence reuse recommendation
- **Prompt:** evidence_reuse_recommendation. **Sample input:** "Which evidence packs can be reused for upcoming audits?" **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected deterministic:** pack availability summary. **Pass:** hybrid; no error.

### TC12 — Delayed closure root cause analysis
- **Prompt:** delayed_closure_root_cause. **Sample input:** "What are common root causes for delayed closure?" **RAM:** local_20gb_extended. **Token:** large_16k.
- **Expected LLM:** root-cause analysis **with confidence + limitations**. **Pass:** llm_assisted.

### TC13 — Audit escalation likelihood
- **Prompt:** audit_escalation_likelihood. **Sample input:** "What is the likelihood of audit escalation?" **RAM:** local_20gb_extended. **Token:** large_16k.
- **Expected LLM:** likelihood with confidence, not certainty. **Pass:** llm_assisted; confidence present.

### TC14 — ServiceNow evidence gap summary
- **Prompt:** service_now_evidence_gap_summary. **Sample input:** "Summarize ServiceNow evidence gaps." **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected deterministic:** evidence-gap figures. **Pass:** hybrid; source references present.

### TC15 — SharePoint evidence availability summary
- **Prompt:** sharepoint_evidence_availability_summary. **Sample input:** "Summarize SharePoint evidence availability." **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected deterministic:** availability/coverage figures. **Pass:** hybrid; no error.

### TC16 — Stale evidence summary
- **Prompt:** stale_evidence_detection_summary. **Sample input:** "Identify stale evidence older than the retention period." **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected deterministic:** stale count vs total. **Pass:** hybrid; deterministic count present.

### TC17 — Audit preparation checklist
- **Prompt:** upcoming_audit_preparation. **Sample input:** "Generate audit preparation notes for the upcoming regulatory review." **RAM:** local_16gb_safe. **Token:** medium_8k.
- **Expected LLM:** prioritized prep notes (live) / fallback. **Pass:** hybrid.

### TC18 — Board-level compliance summary
- **Prompt:** board_level_summary. **RAM:** local_20gb_extended (not 16 GB-supported). **Token:** large_16k.
- **Expected:** on 16 GB the token estimator WARNS this prompt is 20 GB-oriented. **Pass:** runs on 20 GB; warning surfaced on 16 GB.

### TC19 — 16 GB benchmark test
- **Steps:** set RAM = local_16gb_safe, choose Category = observations, click **Run benchmark (dry-run)**, then **Export benchmark**.
- **Expected:** Warnings panel shows a benchmark summary; Export shows written `md`/`json` paths under `reports/audit_llm_benchmarks/`.
- **Pass:** prompts_run ≥ 1; files written; no error.

### TC20 — 20 GB benchmark test
- **Steps:** set RAM = local_20gb_extended, Category = analytics, **Run benchmark (dry-run)** → **Export benchmark**.
- **Expected:** summary with larger token estimates than 16 GB small prompts; files written.
- **Pass:** prompts_run ≥ 1; export succeeds.

---

## Regression checks
- Open the page with no query and click **Classify** → shows a friendly error (query required), no crash.
- **Run prompt** with a `worst_case_enterprise_dry_run` RAM profile → no LLM call, deterministic result + token estimate only.
- With no local provider → **Run prompt** shows `[FALLBACK]` and the deterministic result; app stays responsive.
