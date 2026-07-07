#!/usr/bin/env python3
"""ECS production smoke — fast structural readiness check (offline by default).

Verifies the ECS deployment is wired correctly WITHOUT calling any external
integration. Checks:

  1. app imports                     — the FastAPI app object loads.
  2. audit route registration        — the /api/audit/* routes are registered.
  3. integration adapter registry    — all 9 adapters are registered.
  4. config masking                  — masked_config exposes SET/MISSING, no secrets.
  5. persistence provider selection  — a persistence backend is selectable.
  6. environment variable presence   — required runtime vars are set (advisory
                                        unless --require-env / --strict).
  7. (optional) HTTP endpoints       — with --base-url, probe /api/audit/health etc.

Prints a PASS/FAIL summary. Supports --json and --strict (non-zero exit on any
FAIL). No live external integration is contacted.

USAGE
-----
    python scripts/run_production_smoke.py
    python scripts/run_production_smoke.py --json --strict
    python scripts/run_production_smoke.py --base-url http://127.0.0.1:8000 --strict
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Runtime env vars ECS expects to be set in a real deployment (presence only —
#: values are never read/printed). Absence is advisory unless --require-env.
EXPECTED_ENV_VARS = ("ECS_ENV",)

#: Endpoints probed only when --base-url is supplied.
HTTP_ENDPOINTS = (
    "/api/audit/health",
    "/api/audit/dashboard",
    "/api/audit/integrations",
)


class Check:
    """Accumulates PASS/FAIL results without raising."""

    def __init__(self) -> None:
        self.results: list[dict] = []

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.results.append({"check": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    def summary(self) -> dict:
        passed = sum(1 for r in self.results if r["ok"])
        return {"checks": self.results, "passed": passed,
                "total": len(self.results), "ok": passed == len(self.results)}


# --------------------------------------------------------------------------- #
# Individual checks (each returns via the Check accumulator; never raises)
# --------------------------------------------------------------------------- #
def check_app_imports(chk: Check):
    try:
        from app.main import app  # noqa: F401
        chk.add("app_imports", True, "app.main:app imported")
        return app
    except Exception as exc:  # noqa: BLE001
        chk.add("app_imports", False, f"{type(exc).__name__}: {exc}")
        return None


def check_audit_routes(chk: Check, app) -> None:
    if app is None:
        chk.add("audit_route_registration", False, "app not importable")
        return
    try:
        paths = {getattr(r, "path", "") for r in app.routes}
        required = ["/api/audit/health", "/api/audit/dashboard", "/api/audit/integrations"]
        missing = [p for p in required if p not in paths]
        audit_count = sum(1 for p in paths if p.startswith("/api/audit/"))
        chk.add("audit_route_registration", not missing,
                f"{audit_count} /api/audit/* routes"
                + (f"; missing {missing}" if missing else ""))
    except Exception as exc:  # noqa: BLE001
        chk.add("audit_route_registration", False, f"{type(exc).__name__}: {exc}")


def check_integration_registry(chk: Check) -> None:
    try:
        from modules.operations import integrations
        adapters = integrations.list_adapters()
        chk.add("integration_adapter_registry", len(adapters) == 9,
                f"{len(adapters)} adapters registered")
    except Exception as exc:  # noqa: BLE001
        chk.add("integration_adapter_registry", False, f"{type(exc).__name__}: {exc}")


def check_config_masking(chk: Check) -> None:
    """masked_config_all must expose SET/MISSING and never a raw secret value.

    We inject a canary secret into the environment and assert it does NOT appear
    anywhere in the masked view.
    """
    canary = "SMOKECANARY_" + "X" * 8
    prior = os.environ.get("ECS_JIRA_API_TOKEN")
    try:
        os.environ["ECS_JIRA_API_TOKEN"] = canary
        from modules.operations import integrations
        masked = integrations.masked_config_all()
        blob = json.dumps(masked, default=str)
        leaked = canary in blob
        has_markers = ("SET" in blob) or ("MISSING" in blob)
        chk.add("config_masking", (not leaked) and has_markers,
                "SET/MISSING markers present; no secret leak" if not leaked
                else "SECRET LEAK DETECTED")
    except Exception as exc:  # noqa: BLE001
        chk.add("config_masking", False, f"{type(exc).__name__}: {exc}")
    finally:
        if prior is None:
            os.environ.pop("ECS_JIRA_API_TOKEN", None)
        else:
            os.environ["ECS_JIRA_API_TOKEN"] = prior


def check_persistence_provider(chk: Check) -> None:
    try:
        from modules.audit_intelligence.services import persistence as P
        backend = P.get_persistence()
        is_backend = isinstance(backend, P.AuditPersistence)
        name = type(backend).__name__
        chk.add("persistence_provider", is_backend, f"backend={name}")
    except Exception as exc:  # noqa: BLE001
        chk.add("persistence_provider", False, f"{type(exc).__name__}: {exc}")


def check_env_presence(chk: Check, *, require: bool) -> None:
    missing = [v for v in EXPECTED_ENV_VARS if not os.environ.get(v)]
    ok = (not missing) or (not require)
    detail = "all present" if not missing else f"missing {missing}" + (
        " (advisory)" if not require else "")
    chk.add("environment_variables", ok, detail)


def check_http_endpoints(chk: Check, base_url: str) -> None:
    import urllib.error
    import urllib.request

    base = base_url.rstrip("/")
    for path in HTTP_ENDPOINTS:
        url = f"{base}{path}?role=owner&user=probe"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 - operator-supplied URL
                code = resp.getcode()
            chk.add(f"http {path}", 200 <= code < 400, f"HTTP {code}")
        except urllib.error.HTTPError as exc:
            chk.add(f"http {path}", False, f"HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001
            chk.add(f"http {path}", False, f"{type(exc).__name__}")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(*, base_url: str = "", require_env: bool = False, skip_app: bool = False) -> dict:
    chk = Check()
    app = None
    if skip_app:
        chk.add("app_imports", True, "skipped (--skip-app)")
    else:
        app = check_app_imports(chk)
        check_audit_routes(chk, app)
    check_integration_registry(chk)
    check_config_masking(chk)
    check_persistence_provider(chk)
    check_env_presence(chk, require=require_env)
    if base_url:
        check_http_endpoints(chk, base_url)
    return chk.summary()


def render(report: dict) -> str:
    lines = ["ECS Production Smoke", "===================", ""]
    for r in report["checks"]:
        mark = "PASS" if r["ok"] else "FAIL"
        lines.append(f"  [{mark}] {r['check']:28} {r['detail']}")
    lines.append("")
    lines.append(f"Result: {report['passed']}/{report['total']} checks passed -> "
                 f"{'ALL PASS' if report['ok'] else 'FAILURES PRESENT'}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="ECS production smoke validation (offline by default).")
    parser.add_argument("--base-url", default="",
                        help="If set, probe HTTP endpoints at this base URL.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero if any check fails; also require env vars.")
    parser.add_argument("--require-env", action="store_true",
                        help="Treat missing expected env vars as a failure.")
    parser.add_argument("--skip-app", action="store_true",
                        help="Skip importing the FastAPI app (structural checks only).")
    args = parser.parse_args(argv)

    report = run(base_url=args.base_url,
                 require_env=args.require_env or args.strict,
                 skip_app=args.skip_app)
    print(json.dumps(report, indent=2, default=str) if args.json else render(report))
    if args.strict and not report["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
