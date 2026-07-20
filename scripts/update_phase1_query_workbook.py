#!/usr/bin/env python3
"""Regenerate ECS_Query_Driven_Control_Library_Consolidated_Regenerated.xlsx."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "ECS_Query_Driven_Control_Library_Consolidated_Regenerated.xlsx"

HEADERS = [
    "S.No",
    "Platform",
    "Query/Command/API",
    "Control ID",
    "Control Name",
    "Frameworks",
    "Evidence Type",
    "Phase",
    "Phase-1 Selected",
    "Implementation Status",
    "Executable",
    "Defer Reason",
    "Connector",
    "Target Required",
    "Test Status",
]


def main() -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    from modules.operations.engines import predefined_queries_engine as engine

    engine.load_predefined_queries(force=True)
    controls = sorted(
        [c for c in engine.get_all_controls() if c.get("predefined")],
        key=lambda c: (c.get("technology") or "", c.get("control_id") or ""),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "ECS_Query_Controls"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for i, c in enumerate(controls, start=1):
        status = c.get("status") or ""
        impl = "Ready" if c.get("executable") else status
        test_status = "Automated" if c.get("phase1_selected") else "Deferred"
        ws.append([
            i,
            c.get("technology") or "",
            c.get("query") or "",
            c.get("control_id") or "",
            c.get("control_name") or "",
            c.get("framework_coverage") or ", ".join(c.get("frameworks") or []),
            c.get("evidence_type") or "",
            c.get("phase") or ("Phase1" if c.get("phase1_selected") else "Deferred"),
            "Yes" if c.get("phase1_selected") else "No",
            impl,
            "Yes" if c.get("executable") else "No",
            c.get("defer_reason") or c.get("capability_reason") or "",
            c.get("connector") or "",
            "Yes" if c.get("target_required") else "No",
            test_status,
        ])

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT} ({len(controls)} controls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
