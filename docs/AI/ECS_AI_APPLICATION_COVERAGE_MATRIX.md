# ECS AI Application Coverage Matrix (Phase 5)

**Release tag:** `ecs-local-llm-readiness-enterprise-v1`

**Key fact:** Applications in ECS are **data subjects** (the banking systems being governed), not AI
runtime components. AI/LLM serving is application-agnostic and provider-global (defaults to local
Ollama). Therefore **every governed application is local-LLM ready** — the model never depends on
which application's evidence is being analyzed.

---

## 1. Application catalogs in code (multiple, by module)

| Catalog constant | Count | File:line |
|---|---|---|
| `framework_catalog.APPLICATIONS` | 6 | `framework_catalog.py:10-17` |
| `ecs_state.BANKING_APPLICATIONS` | 20 | `ecs_state.py:15-38` |
| `operations_catalog.BANKING_APPLICATIONS` | 25 | `operations_catalog.py:10-27` |
| `global_filter_engine.APPLICATIONS` | 8 | `global_filter_engine.py:9-12` |

> The canonical demo set is `ecs_state.BANKING_APPLICATIONS` (20 apps). Operations uses a broader 25.

## 2. Requested applications → code presence → readiness

| Requested app | In code? | Closest actual name(s) | Local-LLM ready |
|---|---|---|---|
| Net Banking | **Yes** | Net Banking | ✅ |
| Mobile Banking | **Yes** | Mobile Banking (+ "Mobile Banking Edge") | ✅ |
| Payments | **Yes** | Payments (+ "Payment Switch", "Payments Hub") | ✅ |
| CBS | **Partial** | "Core Banking", "CBS Oracle" | ✅ (variant) |
| UPI | **Yes** | UPI (+ "UPI Gateway") | ✅ |
| LOS | **Partial** | "Loan Origination", "Retail LOS", "Loan System" | ✅ (variant) |
| LMS | **❌ Not found** | — | ❌ (no such app) |
| CRM | **Partial** | "CRM Platform", "CRM" | ✅ (variant) |
| Treasury | **Yes** | Treasury | ✅ |
| Cards | **Partial** | "Cards", "Card Platform", "Credit Card Switch" | ✅ (variant) |
| Merchant Acquiring | **❌ Not exact** | "Merchant Portal" | 🔶 (closest only) |
| API Gateway | **Yes** | API Gateway | ✅ |
| Middleware | **❌ Not an app** | "Middleware Team" (workflow team only) | ❌ (not an application) |
| Authentication Services | **❌ Not found** | — | ❌ (no such app) |

## 3. Additional applications present (not in request, in code)

From `ecs_state.BANKING_APPLICATIONS` / `operations_catalog`: Internet Banking, Retail Banking, Wealth
Portal/Wealth Management, Loan System, Digital Lending, Customer Onboarding, AML Engine, Fraud
Monitoring, ATM Switch, Trade Finance, FX Platform, Corporate Banking, Reconciliation Hub.

## 4. Readiness summary

| Status | Count (vs requested 14) |
|---|---|
| Present (exact or variant) | 10 |
| Closest-only (no exact) | 1 (Merchant Acquiring → Merchant Portal) |
| Not found | 3 (LMS, Middleware-as-app, Authentication Services) |

**All present applications are local-LLM ready** (application-agnostic AI). Gaps are *catalog naming*
issues, not AI gaps. Recommendation (out of scope): normalize a single canonical application catalog
and add missing banking systems if required; no AI change needed.
