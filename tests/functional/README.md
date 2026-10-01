# ECS functional test automation (UC01–UC20)

Reusable framework automating the 331 workbook functional tests. **Implementation only — not executed.**
Full documentation, architecture, gaps and run instructions: [`docs/functional-test-framework.md`](../../docs/functional-test-framework.md).
Traceability (Test ID → test → capability → ECS component → data → expected): [`docs/functional-test-traceability.yaml`](../../docs/functional-test-traceability.yaml).

Skipped by default (`pytest tests/` is unaffected); enable with `--run-functional` / `ECS_FT_ENABLE=1`.
