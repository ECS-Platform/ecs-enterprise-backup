"""Cold/warm refresh early-exit bench."""
import os
import json
import sys
import time
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ECS_AUTH_ENABLED", "false")
os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

print("importing...", flush=True)
from modules.operations.engines import evidence_repository as ops
from ecs_platform.evidence_indexing import suppress_startup_indexing

print("imports ok", flush=True)


def run_once(label):
    print(f"[{label}] clearing ops memory...", flush=True)
    ops.evidence_repository.clear()
    ops.upload_tracker.clear()
    t0 = time.perf_counter()
    with suppress_startup_indexing():
        print(f"[{label}] refresh starting...", flush=True)
        added = ops.refresh_repository_from_frameworks(source="startup")
    dt = time.perf_counter() - t0
    prof = ops._REFRESH_PROFILE or {}
    counts = prof.get("counts") or {}
    result = {
        "label": label,
        "seconds": round(dt, 3),
        "added": added,
        "register_called": counts.get("rows_register_called"),
        "skipped": counts.get("rows_skipped_exists"),
        "catalog": counts.get("catalog_evidences"),
        "total_profile_seconds": prof.get("total_seconds"),
    }
    print(f"[{label}] done: {json.dumps(result)}", flush=True)
    return result


r1 = run_once("first")
r2 = run_once("second_after_durable")
out = {"first": r1, "second": r2, "before_register_calls_expected": 702}
Path("_refresh_early_exit_bench.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print(json.dumps(out, indent=2), flush=True)
sys.exit(0)
