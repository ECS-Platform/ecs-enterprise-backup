# ECS API Reference (Phase 1 supplements)

This folder documents **Phase 1 REST/HTML endpoints** added or extended for specific use cases. The full MVP route surface remains in `modules/shared/routes/routes_mvp.py` and `app/main.py`.

## Documents

| Document | Scope |
|----------|--------|
| [framework_control_master.md](framework_control_master.md) | Framework Control Master catalogue + Evidence Dashboard FCM progress APIs |

## Conventions

- Demo routes accept `role` and `user` query parameters for persona switching when `DEMO_MODE=true`.
- JSON responses include `"ok": true|false` and `"source_type": "file"` for catalogue-backed endpoints.
- Dashboard templates do **not** read YAML; they consume service payloads only.
