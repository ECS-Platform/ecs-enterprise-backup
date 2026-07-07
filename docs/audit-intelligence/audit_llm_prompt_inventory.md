# ECS Audit LLM — Prompt Inventory

The 40 audit prompts in `config/audit_llm_prompt_library.yaml`, loaded + validated
by `modules/audit_intelligence/llm/prompt_library.py`. This inventory is
source-derived; regenerate the counts from the YAML if it changes.

- **Total prompts:** 40
- **query_type mix:** deterministic (DB-first), llm_assisted (predictive/analytical,
  confidence required), hybrid (deterministic + LLM explanation).
- **token profiles:** `small_4k`, `medium_8k`, `large_16k`, `extended_20k`,
  `worst_case_enterprise_dry_run`.
- **local support:** `16gb` = safe on a 16 GB laptop; `20gb` = safe on a 20 GB
  laptop. Prompts marked `no/no` are worst-case enterprise → **dry-run only**.

> See [audit_llm_prompt_workbench_design.md](../workbenches/audit_llm_prompt_workbench_design.md)
> for the deterministic-vs-LLM policy and
> [audit_llm_16gb_20gb_testing_guide.md](../benchmarks/audit_llm_16gb_20gb_testing_guide.md) for
> how to test each profile.

| prompt_id | category | query_type | token_profile | 16gb | 20gb | risk |
|---|---|---|---|---|---|---|
| observation_count | observations | deterministic | small_4k | yes | yes | low |
| high_risk_observation_summary | observations | hybrid | medium_8k | yes | yes | medium |
| framework_gap_analysis | frameworks | hybrid | medium_8k | yes | yes | medium |
| application_audit_readiness | readiness | hybrid | medium_8k | yes | yes | medium |
| csite_closure_probability | prediction | llm_assisted | large_16k | yes | yes | high |
| observation_non_recurrence_probability | prediction | llm_assisted | large_16k | yes | yes | high |
| closure_trend_analysis | analytics | hybrid | medium_8k | yes | yes | medium |
| delayed_closure_root_cause | analytics | llm_assisted | large_16k | yes | yes | high |
| audit_escalation_likelihood | prediction | llm_assisted | large_16k | yes | yes | high |
| evidence_reuse_recommendation | evidence | hybrid | medium_8k | yes | yes | low |
| upcoming_audit_preparation | readiness | hybrid | medium_8k | yes | yes | medium |
| executive_compliance_summary | executive | hybrid | medium_8k | yes | yes | medium |
| board_level_summary | executive | hybrid | large_16k | no | yes | medium |
| application_owner_response | drafting | llm_assisted | medium_8k | yes | yes | medium |
| observation_closure_justification | drafting | llm_assisted | medium_8k | yes | yes | high |
| repeat_observation_analysis | analytics | hybrid | medium_8k | yes | yes | medium |
| technology_compliance_risk | analytics | llm_assisted | medium_8k | yes | yes | medium |
| evidence_gap_to_observation_risk | prediction | llm_assisted | large_16k | yes | yes | high |
| cross_application_comparison | analytics | hybrid | large_16k | yes | yes | medium |
| national_compliance_summary | executive | hybrid | large_16k | no | yes | medium |
| stale_evidence_detection_summary | evidence | hybrid | medium_8k | yes | yes | medium |
| evidence_pack_summary | evidence | hybrid | medium_8k | yes | yes | low |
| service_now_evidence_gap_summary | connectors | hybrid | medium_8k | yes | yes | medium |
| sharepoint_evidence_availability_summary | connectors | hybrid | medium_8k | yes | yes | low |
| audit_query_answering | qa | hybrid | large_16k | yes | yes | medium |
| app_owner_action_summary | operations | hybrid | medium_8k | yes | yes | low |
| cio_compliance_briefing | executive | hybrid | large_16k | no | yes | medium |
| framework_readiness_score_explanation | frameworks | hybrid | medium_8k | yes | yes | low |
| control_failure_history_summary | analytics | hybrid | medium_8k | yes | yes | medium |
| regulatory_reporting_summary | executive | hybrid | large_16k | no | yes | medium |
| risk_acceptance_justification | drafting | llm_assisted | medium_8k | yes | yes | high |
| remediation_recommendation | analytics | llm_assisted | medium_8k | yes | yes | medium |
| audit_observation_drafting | drafting | llm_assisted | medium_8k | yes | yes | high |
| audit_observation_challenge_response | drafting | llm_assisted | medium_8k | yes | yes | high |
| exception_expiry_risk_summary | analytics | hybrid | medium_8k | yes | yes | medium |
| closure_probability_by_owner | prediction | llm_assisted | large_16k | yes | yes | high |
| compliance_trend_forecast | prediction | llm_assisted | extended_20k | no | yes | high |
| application_comparison_summary | analytics | hybrid | medium_8k | yes | yes | low |
| enterprise_evidence_gap_summary | evidence | hybrid | worst_case_enterprise_dry_run | no | no | medium |
| pan_india_dashboard_summary | executive | hybrid | worst_case_enterprise_dry_run | no | no | medium |

## Coverage notes

- **Deterministic-first** prompts (`observation_count`) answer from the ECS
  observation/evidence-gap registry; the LLM only summarizes.
- **Predictive** prompts (`*_probability`, `*_likelihood`, `*_forecast`,
  `*_root_cause`) are `llm_assisted` and emit confidence + assumptions +
  limitations + data used.
- **Worst-case** prompts (`enterprise_evidence_gap_summary`,
  `pan_india_dashboard_summary`) are for the `worst_case_enterprise_dry_run`
  profile: token estimation / prompt-construction validation only.

## Audit query → prompt mapping (examples)

| Example audit query | prompt_id | query_type |
|---|---|---|
| How many observations have been open in Net Banking till date? | observation_count | deterministic |
| How many high-risk observations are open across all frameworks? | high_risk_observation_summary | hybrid |
| Which framework has the highest evidence gap? | framework_gap_analysis | hybrid |
| What are the chances my C-SITE observations will not be raised on Net Banking this year? | csite_closure_probability | llm_assisted |
| What are common root causes for delayed closure? | delayed_closure_root_cause | llm_assisted |
| Generate an executive summary of current audit readiness. | executive_compliance_summary | hybrid |
| Draft closure justification for an observation. | observation_closure_justification | llm_assisted |
| Which applications are least audit-ready? | cross_application_comparison | hybrid |
| Summarize ServiceNow evidence gaps. | service_now_evidence_gap_summary | hybrid |
| Identify stale evidence older than the retention period. | stale_evidence_detection_summary | hybrid |
