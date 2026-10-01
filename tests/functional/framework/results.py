"""Result recording / reporting structure (populated by conftest hooks during a FUTURE execution).

Row fields: Test ID, UC ID, Test Name, Priority, Status, Execution time, Error, Evidence, Request ID, Execution ID, Evidence ID.
Output (written at session end by conftest, only if tests ran): reports/functional_results.json and .csv
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


@dataclass
class ResultRow:
    test_id: str
    uc_id: str
    test_name: str = ""
    priority: str = ""
    test_type: str = ""
    status: str = ""            # passed | failed | skipped(blocked) | error
    duration_sec: float = 0.0
    error: str = ""
    skip_reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    execution_id: str = ""      # ECS run_id
    evidence_id: str = ""


class ResultRecorder:
    def __init__(self) -> None:
        self.rows: list[ResultRow] = []

    def add(self, row: ResultRow) -> None:
        self.rows.append(row)

    def write(self, directory: Path | None = None) -> list[Path]:
        if not self.rows:
            return []
        out = directory or REPORTS_DIR
        out.mkdir(parents=True, exist_ok=True)
        j, c = out / "functional_results.json", out / "functional_results.csv"
        j.write_text(json.dumps([asdict(r) for r in self.rows], indent=2, default=str), encoding="utf-8")
        with open(c, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            cols = ["test_id", "uc_id", "test_name", "priority", "test_type", "status", "duration_sec", "error",
                    "skip_reason", "request_id", "execution_id", "evidence_id"]
            w.writerow(cols)
            for r in self.rows:
                d = asdict(r)
                w.writerow([d[k] for k in cols])
        return [j, c]

    def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows:
            out[r.status] = out.get(r.status, 0) + 1
        return out
