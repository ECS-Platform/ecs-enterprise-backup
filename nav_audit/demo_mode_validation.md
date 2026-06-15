# ECS Demo Mode — Permanent Fix Validation

**Objective:** Guarantee `DEMO_MODE` / `ECS_AUTH_ENABLED` are loaded from `.env`
into `os.environ` at process start (before any authentication initialisation),
so browser refresh never triggers an auth failure in demo mode.

## Changes
1. **`python-dotenv` added** to `requirements.txt` and installed in the runtime
   interpreter (`python-dotenv==1.2.2`).
2. **`app/env_bootstrap.py`** (new): loads the repo-root `.env` into
   `os.environ` exactly once, using `python-dotenv` when available and a tiny
   built-in parser as a fallback. `override=False` so container/CI env still
   wins. Never raises.
3. **`app/main.py`**: `from app import env_bootstrap` is now the **first import**
   (before `app.*` / `modules.*` / auth), so the flags exist by the time
   authentication, RBAC and page guards initialise.
4. **Startup logging** added to the lifespan:
   ```
   ECS Startup
   DEMO_MODE=<value>
   ECS_AUTH_ENABLED=<value>
   .env loaded=<bool> via <parser>
   ```

## Verification (live server)

Startup log:
```
[ECSStartup] ECS Startup
[ECSStartup] DEMO_MODE=true
[ECSStartup] ECS_AUTH_ENABLED=false
[ECSStartup] .env loaded=True via python-dotenv
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

HTTP checks:
| Request | Result |
|---|---|
| `GET /dashboard?role=cio&user=cio` | 200 |
| `GET /mvp/enterprise?role=auditor&user=auditor` | 200 |
| `GET /dashboard` (no role — refresh/auth-bounce test) | 200 (no redirect to login) |

## Result
- `.env` values are loaded automatically at startup. ✅
- `DEMO_MODE=true` and `ECS_AUTH_ENABLED=false` confirmed in process env. ✅
- Startup banner present. ✅
- No authentication failure on refresh / token-free navigation. ✅
