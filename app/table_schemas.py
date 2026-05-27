"""Table column schemas — single source of truth for header ↔ field alignment."""

from __future__ import annotations

# table_id → (headers, field_keys)
TABLE_SCHEMAS: dict[str, dict] = {
    "reuse-main": {
        "headers": [
            "Reuse ID", "Source Framework", "Target Framework", "Application",
            "Control ID", "Control Name", "Reused Evidence", "Reuse Type",
            "Reuse Status", "Approved By", "Last Reviewed", "Audit Savings", "Actions",
        ],
        "fields": [
            "reuse_id", "source_framework", "target_framework", "application",
            "control_id", "control_name", "reused_evidence_file", "reuse_type",
            "reuse_status", "approved_by", "last_reviewed", "audit_savings_hrs", None,
        ],
        "colspan": 13,
    },
    "reuse-mappings": {"inherit": "reuse-main"},
    "reuse-pending": {"inherit": "reuse-main"},
    "health-queue": {"colspan": 16},
    "audit-gaps": {"colspan": 11},
    "audit-upcoming": {"colspan": 12},
    "exceptions-list": {"colspan": 9},
    "search-results": {"colspan": 7},
}


def schema_colspan(table_id: str) -> int:
    s = TABLE_SCHEMAS.get(table_id, {})
    if "inherit" in s:
        s = TABLE_SCHEMAS.get(s["inherit"], {})
    return s.get("colspan", 8)
