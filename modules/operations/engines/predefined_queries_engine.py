"""Predefined Queries — load controls from ECS_Query_Driven_Control_Library_Consolidated.xlsx."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from modules.operations.engines.predefined_query_audit import (
    get_execution_audit_log,
    get_execution_history_for_control,
    record_execution_audit,
)
from modules.operations.engines.predefined_query_evidence import (
    get_latest_evidence_for_control,
    prepare_evidence_record,
    register_with_evidence_repository,
)
from modules.shared.utils.pagination import paginate

EXCEL_FILENAME = "ECS_Query_Driven_Control_Library_Consolidated.xlsx"

HEADER_ALIASES: dict[str, list[str]] = {
    "control_id": ["control id", "controlid", "control_id", "id", "control ref", "control reference"],
    "control_name": ["control name", "controlname", "control_name", "name", "control title", "title"],
    "framework_coverage": [
        "framework coverage",
        "frameworks",
        "framework",
        "framework mapping",
        "framework(s)",
        "applicable frameworks",
    ],
    "query": ["query", "predefined query", "sql query", "command", "script", "check query", "validation query"],
    "description": ["description", "control description", "desc", "details", "requirement description"],
    "evidence_type": ["evidence type", "evidencetype", "evidence_type", "expected evidence", "evidence"],
}

TECHNOLOGY_RULES: list[tuple[str, list[str]]] = [
    ("GitLeaks", ["gitleaks detect", "gitleaks"]),
    ("Trivy", ["trivy image", "trivy"]),
    ("SonarQube", ["/api/issues/search", "sonarqube"]),
    ("NGINX", ["nginx -t", "nginx -T"]),
    ("PostgreSQL", ["pg_stat_replication", "show ssl", "show password_encryption", "from pg_", " pg_"]),
    ("Oracle", ["dba_role_privs", "v$encryption_wallet", " v$", " dba_", "from dba_"]),
    ("Windows", ["get-hotfix", "get-mpcomputerstatus", "get-aduser", "powershell"]),
    ("Linux", ["df -h", "free -m", "timedatectl", "cat /etc/ssh/sshd_config", "/etc/ssh", "systemctl status"]),
]

ALLOWED_POSTGRESQL_QUERIES: frozenset[str] = frozenset({
    "show ssl;",
    "show password_encryption;",
    "select * from pg_stat_replication;",
})

_controls: list[dict[str, Any]] = []
_validation_report: dict[str, Any] = {}
_loaded = False
_errors_found: list[str] = []
_errors_fixed: list[str] = []


def _connector_config_loaded() -> bool:
    from modules.operations.engines.query_connectors import CONNECTOR_CONFIG

    return bool(CONNECTOR_CONFIG)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _excel_path() -> Path:
    return _repo_root() / EXCEL_FILENAME


def _normalize_header(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _resolve_header_index(headers: list[str]) -> dict[str, int | None]:
    mapping: dict[str, int | None] = {key: None for key in HEADER_ALIASES}
    for idx, header in enumerate(headers):
        h = _normalize_header(header)
        if not h:
            continue
        for field, aliases in HEADER_ALIASES.items():
            if mapping[field] is not None:
                continue
            if h in aliases or any(alias in h for alias in aliases):
                mapping[field] = idx
    return mapping


def _cell_value(row: tuple, index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    value = row[index]
    if value is None:
        return ""
    return str(value).strip()


def _parse_frameworks(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;|/\n]+", raw)
    frameworks = []
    seen: set[str] = set()
    for part in parts:
        fw = part.strip()
        if fw and fw.lower() not in seen:
            seen.add(fw.lower())
            frameworks.append(fw)
    return frameworks


def detect_technology(query: str) -> str:
    """Deterministic technology detection from query text — no AI."""
    if not query or not query.strip():
        return ""
    q = query.lower()
    for technology, patterns in TECHNOLOGY_RULES:
        for pattern in patterns:
            if pattern.lower() in q:
                return technology
    return "Unknown"


def _derive_status(control: dict[str, Any]) -> str:
    if not control.get("predefined"):
        return "Manual"
    technology = control.get("technology") or ""
    if not technology or technology == "Unknown":
        return "Unsupported Technology"
    return "Ready"


def _last_execution(control_id: str) -> str:
    history = get_execution_history_for_control(control_id, limit=1)
    if history:
        return history[0].get("execution_time", "—")
    return "Not Executed"


def _load_from_excel() -> tuple[list[dict[str, Any]], list[str]]:
    path = _excel_path()
    errors: list[str] = []
    if not path.is_file():
        errors.append(f"Excel file not found: {path}")
        return [], errors

    try:
        from openpyxl import load_workbook
    except ImportError:
        errors.append("openpyxl is required to load the control library Excel file")
        return [], errors

    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        errors.append(f"Failed to open Excel workbook: {exc}")
        return [], errors

    sheet = None
    for name in workbook.sheetnames:
        if "consolidated" in name.lower() or "query" in name.lower() or "control" in name.lower():
            sheet = workbook[name]
            break
    if sheet is None:
        sheet = workbook[workbook.sheetnames[0]]

    rows_iter = sheet.iter_rows(values_only=True)
    header_row: tuple | None = None
    header_index = 0
    buffered: list[tuple] = []

    for i, row in enumerate(rows_iter):
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue
        headers = [_normalize_header(cell) for cell in row]
        mapping = _resolve_header_index(list(row))
        matched = sum(1 for v in mapping.values() if v is not None)
        if matched >= 3:
            header_row = row
            header_index = i
            break
        if i < 10:
            buffered.append(row)

    if header_row is None:
        for row in buffered:
            mapping = _resolve_header_index(list(row))
            if sum(1 for v in mapping.values() if v is not None) >= 2:
                header_row = row
                break

    if header_row is None:
        errors.append("Could not detect header row in Excel — expected Control ID, Control Name, Query columns")
        workbook.close()
        return [], errors

    col_map = _resolve_header_index(list(header_row))
    if col_map["control_id"] is None and col_map["control_name"] is None:
        errors.append("Excel header row missing Control ID and Control Name columns")
        workbook.close()
        return [], errors

    controls: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    row_num = 0

    for row in sheet.iter_rows(values_only=True):
        row_num += 1
        if row_num <= header_index + 1:
            continue
        if not row or all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        control_id = _cell_value(row, col_map["control_id"])
        control_name = _cell_value(row, col_map["control_name"])
        framework_raw = _cell_value(row, col_map["framework_coverage"])
        query = _cell_value(row, col_map["query"])
        description = _cell_value(row, col_map["description"])
        evidence_type = _cell_value(row, col_map["evidence_type"])

        if not control_id and not control_name:
            continue
        if not control_id:
            control_id = control_name
        if control_id in seen_ids:
            errors.append(f"Duplicate Control ID skipped: {control_id}")
            continue
        seen_ids.add(control_id)

        frameworks = _parse_frameworks(framework_raw)
        predefined = bool(query)
        technology = detect_technology(query) if predefined else ""

        record = {
            "control_id": control_id,
            "control_name": control_name or control_id,
            "framework_coverage": ", ".join(frameworks) if frameworks else framework_raw,
            "frameworks": frameworks,
            "query": query,
            "description": description,
            "evidence_type": evidence_type,
            "predefined": predefined,
            "technology": technology,
            "status": "",
            "last_execution": "Not Executed",
        }
        record["status"] = _derive_status(record)
        controls.append(record)

    workbook.close()
    if not controls:
        errors.append("No control rows loaded from Excel")
    return controls, errors


def load_predefined_queries(*, force: bool = False) -> dict[str, Any]:
    """Load controls from Excel (idempotent)."""
    global _controls, _validation_report, _loaded, _errors_found, _errors_fixed

    if _loaded and not force:
        return _validation_report

    _errors_found = []
    _errors_fixed = []
    controls, load_errors = _load_from_excel()
    _errors_found.extend(load_errors)

    for ctrl in controls:
        if ctrl.get("predefined") and not ctrl.get("frameworks"):
            _errors_found.append(f"Missing framework mapping for {ctrl['control_id']}")
        if ctrl.get("predefined") and ctrl.get("technology") == "Unknown":
            _errors_found.append(f"Unsupported technology for {ctrl['control_id']}")

    for ctrl in controls:
        ctrl["last_execution"] = _last_execution(ctrl["control_id"])

    _controls = controls
    predefined_count = sum(1 for c in controls if c.get("predefined"))
    manual_count = len(controls) - predefined_count
    frameworks_covered = sorted({fw for c in controls for fw in c.get("frameworks", [])})

    _validation_report = {
        "excel_loaded": bool(controls) and not load_errors,
        "excel_path": str(_excel_path()),
        "controls_loaded": len(controls),
        "predefined_controls": predefined_count,
        "manual_controls": manual_count,
        "queries_loaded": predefined_count,
        "frameworks_covered": frameworks_covered,
        "technology_rules_loaded": len(TECHNOLOGY_RULES) > 0,
        "connector_configuration_loaded": _connector_config_loaded(),
        "errors_found": list(_errors_found),
        "errors_fixed": list(_errors_fixed),
    }
    _loaded = True
    return _validation_report


def validate_startup() -> dict[str, Any]:
    """Startup validation — returns report and log lines for terminal output."""
    report = load_predefined_queries()
    lines = [
        f"Excel Loaded: {'Yes' if report['excel_loaded'] else 'No'} ({report['excel_path']})",
        f"Controls Loaded: {report['controls_loaded']}",
        f"Predefined Controls: {report['predefined_controls']}",
        f"Manual Controls: {report['manual_controls']}",
        f"Queries Loaded: {report['queries_loaded']}",
        f"Frameworks Covered: {len(report['frameworks_covered'])} — {', '.join(report['frameworks_covered'][:8])}{'…' if len(report['frameworks_covered']) > 8 else ''}",
        f"Technology Rules Loaded: {report['technology_rules_loaded']}",
        f"Connector Configuration Loaded: {report['connector_configuration_loaded']}",
        f"Errors Found: {len(report['errors_found'])}",
        f"Errors Fixed: {len(report['errors_fixed'])}",
    ]
    if report["errors_found"]:
        for err in report["errors_found"][:5]:
            lines.append(f"  — {err}")
        if len(report["errors_found"]) > 5:
            lines.append(f"  — … and {len(report['errors_found']) - 5} more")
    report["log_lines"] = lines
    return report


def get_all_controls() -> list[dict[str, Any]]:
    if not _loaded:
        load_predefined_queries()
    return list(_controls)


def _normalize_query_allowlist(query: str) -> str:
    q = re.sub(r"\s+", " ", query.strip().lower())
    if q and not q.endswith(";"):
        q += ";"
    return q


def is_postgresql_execution_enabled(control: dict[str, Any]) -> bool:
    if not control.get("predefined"):
        return False
    if control.get("technology") != "PostgreSQL":
        return False
    normalized = _normalize_query_allowlist(control.get("query") or "")
    return normalized in ALLOWED_POSTGRESQL_QUERIES


def _refresh_control_last_execution(control_id: str) -> None:
    last = _last_execution(control_id)
    for ctrl in _controls:
        if ctrl["control_id"] == control_id:
            ctrl["last_execution"] = last
            break


def get_control_by_id(control_id: str) -> dict[str, Any] | None:
    for ctrl in get_all_controls():
        if ctrl["control_id"] == control_id:
            enriched = dict(ctrl)
            history = get_execution_history_for_control(control_id)
            enriched["execution_history"] = history
            enriched["latest_result"] = get_latest_evidence_for_control(control_id)
            enriched["latest_execution"] = history[0] if history else None
            return enriched
    return None


def get_framework_filter_options() -> list[str]:
    frameworks = {"All Frameworks"}
    for ctrl in get_all_controls():
        for fw in ctrl.get("frameworks", []):
            frameworks.add(fw)
    return ["All Frameworks"] + sorted(frameworks - {"All Frameworks"})


def filter_controls(
    *,
    search: str = "",
    framework: str = "All Frameworks",
    predefined_only: bool = False,
    sort_by: str = "control_id",
    sort_dir: str = "asc",
) -> list[dict[str, Any]]:
    rows = get_all_controls()
    q = search.strip().lower()

    if framework and framework != "All Frameworks":
        rows = [r for r in rows if framework in r.get("frameworks", []) or framework in (r.get("framework_coverage") or "")]

    if predefined_only:
        rows = [r for r in rows if r.get("predefined")]

    if q:
        rows = [
            r
            for r in rows
            if q in r["control_id"].lower()
            or q in r["control_name"].lower()
            or q in (r.get("query") or "").lower()
            or q in (r.get("framework_coverage") or "").lower()
            or q in (r.get("technology") or "").lower()
        ]

    reverse = sort_dir.lower() == "desc"
    sort_key = sort_by if sort_by in ("control_id", "control_name", "technology", "status", "last_execution") else "control_id"
    rows.sort(key=lambda r: (r.get(sort_key) or "").lower(), reverse=reverse)
    return rows


def get_predefined_queries_dashboard(
    *,
    search: str = "",
    framework: str = "All Frameworks",
    page: int = 1,
    per_page: int = 10,
    sort_by: str = "control_id",
    sort_dir: str = "asc",
    predefined_only: bool = False,
) -> dict[str, Any]:
    """Build dashboard payload for the Predefined Queries page."""
    report = load_predefined_queries()
    filtered = filter_controls(
        search=search,
        framework=framework,
        predefined_only=predefined_only,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    page_data = paginate(filtered, page=page, per_page=per_page)

    predefined_rows = [r for r in get_all_controls() if r.get("predefined")]
    manual_rows = [r for r in get_all_controls() if not r.get("predefined")]
    unsupported = [r for r in predefined_rows if r.get("technology") == "Unknown"]

    return {
        "validation": report,
        "rows": page_data["items"],
        "pagination": page_data,
        "framework_options": get_framework_filter_options(),
        "search": search,
        "framework_filter": framework,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
        "predefined_only": predefined_only,
        "kpis": [
            {"label": "Total Controls", "value": report["controls_loaded"], "tone": "primary"},
            {"label": "Predefined Queries", "value": report["predefined_controls"], "tone": "success"},
            {"label": "Manual Controls", "value": report["manual_controls"], "tone": "secondary"},
            {"label": "Frameworks Covered", "value": len(report["frameworks_covered"]), "tone": "info"},
            {"label": "Unsupported Tech", "value": len(unsupported), "tone": "warning"},
        ],
        "all_predefined_count": len(predefined_rows),
        "manual_count": len(manual_rows),
        "unsupported_count": len(unsupported),
        "execution_enabled": True,
        "execution_history_rows": get_execution_audit_log(limit=100),
    }


def prepare_execution(control_id: str, user: str) -> dict[str, Any]:
    """
    Prepare execution context (interfaces only — does not execute).
    Returns structured response for UI; never raises to caller.
    """
    control = get_control_by_id(control_id)
    if not control:
        return {"ok": False, "error": "Control not found", "error_type": "missing_control"}

    if not control.get("query"):
        return {"ok": False, "error": "Missing query for this control", "error_type": "missing_query"}

    technology = control.get("technology") or ""
    if not technology or technology == "Unknown":
        return {
            "ok": False,
            "error": "Technology could not be determined for this query",
            "error_type": "unsupported_technology",
        }

    if not control.get("frameworks") and not control.get("framework_coverage"):
        return {
            "ok": False,
            "error": "Framework mapping missing for this control",
            "error_type": "missing_framework",
        }

    from modules.operations.engines.query_connectors import connector_for_technology

    connector = connector_for_technology(technology)
    if connector is None:
        return {
            "ok": False,
            "error": f"No connector available for technology: {technology}",
            "error_type": "unsupported_technology",
        }

    execution_enabled = technology == "PostgreSQL" and is_postgresql_execution_enabled(control)
    return {
        "ok": True,
        "execution_enabled": execution_enabled,
        "message": "PostgreSQL execution enabled" if execution_enabled else "Execution not enabled for this technology",
        "control_id": control_id,
        "technology": technology,
        "connector": type(connector).__name__,
        "user": user,
    }


def run_postgresql_query(control_id: str, user: str) -> dict[str, Any]:
    """Execute a predefined PostgreSQL query from the Excel catalog."""
    control = get_control_by_id(control_id)
    if not control:
        return {"ok": False, "error": "Control not found", "error_type": "missing_control"}

    query = (control.get("query") or "").strip()
    if not query:
        return {"ok": False, "error": "Missing query for this control", "error_type": "missing_query"}

    if control.get("technology") != "PostgreSQL":
        return {
            "ok": False,
            "error": "Live execution is only enabled for PostgreSQL controls",
            "error_type": "unsupported_technology",
        }

    if _normalize_query_allowlist(query) not in ALLOWED_POSTGRESQL_QUERIES:
        return {
            "ok": False,
            "error": "This PostgreSQL query is not enabled for live demo execution",
            "error_type": "unsupported_query",
        }

    from modules.operations.engines.postgresql_connector import PostgreSQLConnector, get_postgresql_config

    connector = PostgreSQLConnector(**get_postgresql_config())
    framework_coverage = control.get("framework_coverage") or ""

    if not connector.connect():
        record_execution_audit(
            control_id,
            user,
            "PostgreSQL",
            "Failed",
            error_message=connector._last_error or "Connection failed",
            framework_coverage=framework_coverage,
            query=query,
        )
        _refresh_control_last_execution(control_id)
        return {
            "ok": False,
            "error": connector._last_error or "Could not connect to PostgreSQL",
            "error_type": "connection_failure",
        }

    try:
        result = connector.execute(query)
    finally:
        connector.disconnect()

    rows_returned = int(result.metadata.get("rows_returned", 0)) if result.metadata else 0

    if not result.success:
        record_execution_audit(
            control_id,
            user,
            "PostgreSQL",
            "Failed",
            duration_ms=result.duration_ms,
            error_message=result.error_message,
            framework_coverage=framework_coverage,
            query=query,
            result=result.output,
            rows_returned=rows_returned,
        )
        _refresh_control_last_execution(control_id)
        return {
            "ok": False,
            "error": result.error_message,
            "error_type": result.metadata.get("error_type", "query_failure") if result.metadata else "query_failure",
        }

    record_execution_audit(
        control_id,
        user,
        "PostgreSQL",
        "Success",
        duration_ms=result.duration_ms,
        framework_coverage=framework_coverage,
        query=query,
        result=result.output,
        rows_returned=rows_returned,
    )

    evidence = prepare_evidence_record(
        control_id=control_id,
        result=result.output,
        user=user,
        framework_coverage=framework_coverage,
    )
    primary_fw = control.get("frameworks", [""])[0] if control.get("frameworks") else ""
    register_with_evidence_repository(evidence, framework=primary_fw)
    _refresh_control_last_execution(control_id)

    from modules.shared.services.audit_trail import log_event

    log_event(
        "Predefined Query Executed",
        user,
        primary_fw,
        control_id,
        f"PostgreSQL — {rows_returned} rows — {result.duration_ms}ms",
    )

    return {
        "ok": True,
        "message": f"Query executed successfully — {rows_returned} row(s) returned in {result.duration_ms}ms",
        "control_id": control_id,
        "query": query,
        "status": "Success",
        "rows_returned": rows_returned,
        "output": result.output,
        "duration_ms": result.duration_ms,
        "evidence_id": evidence.evidence_id,
    }
