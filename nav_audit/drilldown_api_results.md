# Drilldown API — Real Request Results

Requests executed live against the running server (`http://127.0.0.1:8000`). Not code inspection.

## The four reported KPIs (role=owner)

| KPI | URL | Status | Time | ok | Rows |
|---|---|---|---|---|---|
| Closure Rate | `/api/ecs/workflow-drill?metric=approval_rate&count=10&role=owner` | 200 | 22 ms | true | 25 |
| Avg Review Time | `/api/ecs/workflow-drill?metric=avg_review_time&count=10&role=owner` | 200 | 2 ms | true | 25 |
| Rejection Trend | `/api/ecs/workflow-drill?metric=rejection_trend&count=10&role=owner` | 200 | 2 ms | true | 25 |
| Auditor SLA | `/api/ecs/workflow-drill?metric=auditor_sla&count=10&role=owner` | 200 | 1 ms | true | 25 |
| Pending Aging | `/api/ecs/workflow-drill?metric=pending_aging&count=10&role=owner` | 200 | 2 ms | true | 25 |

Confirmed identical results for `role=cio` and `role=auditor` (all 200 / ok=true / 25 rows / 1-2 ms).

## Response shape (auditor_sla, owner)

```json
{
  "ok": true,
  "title": "Auditor SLA — Evidence Workflow",
  "columns": ["application","framework","domain","control","evidence","observation",
              "finding","owner","reviewer","status","risk","created_date","updated_date"],
  "rows": [ { "application":"Loan Origination", "framework":"OS Baselining",
              "domain":"Network Security", "control":"OS B-56 — Encryption",
              "owner":"H. Singh", "status":"Open", "risk":"Low", ... }, ... 25 total ],
  "sections": { "approval_history": [ ... ] },
  "metric_trace": { "metric_name":"...", "calculation_formula": { ... } },
  "detail": { "metric_name":"...", "formula":"Readiness = 10 / 70", "result":"14.3%" },
  "trace_count": <n>, "row_count": <n>, "metric": "auditor_sla", "role": "owner"
}
```

**Conclusion:** the backend was never the failure. Every metric returns HTTP 200, `ok:true`,
25 populated rows, in ~1-2 ms. The defect was entirely client-side (see root cause below).
