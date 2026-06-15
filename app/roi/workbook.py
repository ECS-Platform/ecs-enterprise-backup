"""ROI workbook reader — the authoritative executive data source.

Reads ``ROI.xlsx`` directly (stdlib only: zipfile + ElementTree; NO openpyxl,
NO third-party deps) and exposes a structured, board-ready view-model for the
ROI Center presentation layer.

IMPORTANT — presentation only:
  * This module DOES NOT recompute the workbook's numbers. It reads the values
    the workbook already contains (totals, per-framework rows, scenarios, FTE,
    storage, executive dashboard) and only performs *presentation* aggregation
    (top-N contributors, "+N additional frameworks" grouping, contribution %,
    KPI tiering, traceability chain).
  * The existing deterministic ROI engine (app/roi/calculations.py etc.) is
    untouched; this is an additive, read-only data feed for storytelling.
  * Every public function is fail-safe: on any error it returns an empty/typed
    structure so the page can never crash because of the workbook.
"""

from __future__ import annotations

import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

_CRORE = 10_000_000
_LAKH = 100_000


# --------------------------------------------------------------------------- #
# Currency formatting (mirrors app.roi.models.format_inr for consistency)
# --------------------------------------------------------------------------- #

def fmt_inr(n: float) -> str:
    n = float(n or 0)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= _CRORE:
        return f"{sign}\u20b9{_trim(n / _CRORE)} Cr"
    if n >= _LAKH:
        return f"{sign}\u20b9{_trim(n / _LAKH)} Lakh"
    return f"{sign}\u20b9{int(round(n)):,}"


def fmt_cr(cr: float) -> str:
    """Format a value already expressed in Crore."""
    return f"\u20b9{_trim(float(cr or 0))} Cr"


def fmt_cr_exec(cr: float) -> str:
    """Executive Crore format: ₹X.XX Cr (2 dp), but 1 dp for values >= 100.

    Examples: 0.06468 -> ₹0.06 Cr, 2.255 -> ₹2.26 Cr, 143.08 -> ₹143.1 Cr.
    """
    v = float(cr or 0)
    dp = 1 if abs(v) >= 100 else 2
    return f"\u20b9{_round_half_up(v, dp):.{dp}f} Cr"


def fmt_k(n: float) -> str:
    """Executive large-number format with K/M suffix and one decimal.

    Examples: 45438 -> 45.4K, 90000 -> 90K, 180000 -> 180K, 9554 -> 9.6K.
    """
    v = float(n or 0)
    sign = "-" if v < 0 else ""
    v = abs(v)
    if v >= 1_000_000:
        return f"{sign}{_k_trim(v / 1_000_000)}M"
    if v >= 1_000:
        return f"{sign}{_k_trim(v / 1_000)}K"
    return f"{sign}{int(round(v)):,}"


def fmt_fte(n: float) -> str:
    """FTE format with one decimal: 22.72 -> 22.7."""
    return f"{_round_half_up(float(n or 0), 1):.1f}"


def fmt_label_1dp(n: float) -> str:
    """Bar-chart label rounded to one decimal: 143.08 -> 143.1, 88.60 -> 88.6."""
    return f"{_round_half_up(float(n or 0), 1):.1f}"


def fmt_num(n: float) -> str:
    return f"{int(round(float(n or 0))):,}"


def _round_half_up(x: float, dp: int) -> float:
    """Round half away from zero (so 2.255 -> 2.26, not banker's rounding)."""
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-dp)  # 10^-dp
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def _k_trim(x: float) -> str:
    """One-decimal trim that drops a trailing .0 (90.0 -> 90, 45.4 -> 45.4)."""
    r = _round_half_up(x, 1)
    return f"{r:g}" if r == int(r) else f"{r:.1f}"


def _trim(x: float) -> str:
    return f"{round(x, 2):g}"


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #

@dataclass
class FrameworkRow:
    name: str = ""
    applications: int = 0
    observations_per_app: float = 0.0
    total_observations: int = 0
    emails_per_observation: float = 0.0
    emails_saved: int = 0
    hours_saved: float = 0.0
    cost_per_hour: float = 0.0
    annual_saving_cr: float = 0.0
    justification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "applications": self.applications,
            "observations_per_app": self.observations_per_app,
            "total_observations": self.total_observations,
            "emails_per_observation": self.emails_per_observation,
            "emails_saved": self.emails_saved, "hours_saved": self.hours_saved,
            "cost_per_hour": self.cost_per_hour,
            "annual_saving_cr": self.annual_saving_cr,
            "annual_saving_display": fmt_cr(self.annual_saving_cr),
            "hours_display": fmt_num(self.hours_saved),
            "observations_display": fmt_num(self.total_observations),
            "justification": self.justification,
        }


@dataclass
class YearPoint:
    label: str = ""
    applications: int = 0
    annual_savings_cr: float = 0.0
    cumulative_savings_cr: float = 0.0
    ecs_cost_cr: float = 0.0
    cumulative_cost_cr: float = 0.0
    net_benefit_cr: float = 0.0
    payback_status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label, "applications": self.applications,
            "annual_savings_cr": self.annual_savings_cr,
            "cumulative_savings_cr": self.cumulative_savings_cr,
            "ecs_cost_cr": self.ecs_cost_cr,
            "cumulative_cost_cr": self.cumulative_cost_cr,
            "net_benefit_cr": self.net_benefit_cr,
            "payback_status": self.payback_status,
            "annual_savings_display": fmt_cr(self.annual_savings_cr),
            "cumulative_savings_display": fmt_cr(self.cumulative_savings_cr),
            "net_benefit_display": fmt_cr(self.net_benefit_cr),
        }


@dataclass
class StorageRow:
    area: str = ""
    volume: str = ""
    reduction: str = ""
    annual_saving_cr: float = 0.0
    justification: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"area": self.area, "volume": self.volume, "reduction": self.reduction,
                "annual_saving_cr": self.annual_saving_cr,
                "annual_saving_display": fmt_cr(self.annual_saving_cr),
                "justification": self.justification}


@dataclass
class WorkbookModel:
    available: bool = False
    source: str = ""
    frameworks: list[FrameworkRow] = field(default_factory=list)
    years: list[YearPoint] = field(default_factory=list)
    storage: list[StorageRow] = field(default_factory=list)
    # workbook totals (read straight from the workbook)
    total_frameworks: int = 0
    total_applications: int = 0
    total_observations: int = 0
    total_emails_saved: int = 0
    total_hours_saved: float = 0.0
    total_annual_saving_cr: float = 0.0
    fte_equivalent: float = 0.0
    cost_per_hour: float = 0.0
    average_salary: float = 0.0
    storage_total_cr: float = 0.0
    three_year_value_cr: float = 0.0
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available, "source": self.source, "note": self.note,
            "frameworks": [f.to_dict() for f in self.frameworks],
            "years": [y.to_dict() for y in self.years],
            "storage": [s.to_dict() for s in self.storage],
            "total_frameworks": self.total_frameworks,
            "total_applications": self.total_applications,
            "total_observations": self.total_observations,
            "total_emails_saved": self.total_emails_saved,
            "total_hours_saved": self.total_hours_saved,
            "total_annual_saving_cr": self.total_annual_saving_cr,
            "fte_equivalent": self.fte_equivalent,
            "cost_per_hour": self.cost_per_hour,
            "average_salary": self.average_salary,
            "storage_total_cr": self.storage_total_cr,
            "three_year_value_cr": self.three_year_value_cr,
            # display helpers
            "total_observations_display": fmt_num(self.total_observations),
            "total_emails_display": fmt_num(self.total_emails_saved),
            "total_hours_display": fmt_num(self.total_hours_saved),
            "total_annual_display": fmt_cr(self.total_annual_saving_cr),
            "three_year_display": fmt_cr(self.three_year_value_cr),
            "storage_total_display": fmt_cr(self.storage_total_cr),
        }


# --------------------------------------------------------------------------- #
# xlsx parsing (stdlib)
# --------------------------------------------------------------------------- #

def workbook_path() -> Path:
    override = os.environ.get("ROI_WORKBOOK_PATH")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "ROI.xlsx"


def _num(v: Any) -> float:
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _read_sheets(path: Path) -> dict[str, list[list[str]]]:
    """Return {sheet_name: rows[][]} as strings. Stdlib only. Never raises."""
    out: dict[str, list[list[str]]] = {}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{_NS}si"):
                shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid2tgt = {r.get("Id"): r.get("Target") for r in rels}
        sheets_el = wb.find(f"{_NS}sheets")
        if sheets_el is None:
            return out
        for s in sheets_el.findall(f"{_NS}sheet"):
            name = s.get("name") or ""
            rid = s.get(f"{_R_NS}id")
            tgt = rid2tgt.get(rid, "")
            if not tgt:
                continue
            spath = tgt.lstrip("/") if tgt.startswith("/") else "xl/" + tgt
            if spath not in names:
                continue
            root = ET.fromstring(z.read(spath))
            rows: list[list[str]] = []
            for row in root.iter(f"{_NS}row"):
                cells: dict[int, str] = {}
                maxc = 0
                for c in row.findall(f"{_NS}c"):
                    ref = c.get("r") or ""
                    m = re.match(r"([A-Z]+)(\d+)", ref)
                    if not m:
                        continue
                    col = _col_index(m.group(1))
                    maxc = max(maxc, col)
                    t = c.get("t")
                    v = c.find(f"{_NS}v")
                    val = ""
                    if v is not None and v.text is not None:
                        val = v.text
                        if t == "s":
                            try:
                                val = shared[int(val)]
                            except (ValueError, IndexError):
                                val = ""
                    else:
                        isv = c.find(f"{_NS}is")
                        if isv is not None:
                            val = "".join(x.text or "" for x in isv.iter(f"{_NS}t"))
                    cells[col] = val
                rows.append([cells.get(i, "") for i in range(maxc + 1)])
            out[name] = rows
    return out


def _col_index(letters: str) -> int:
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


# --------------------------------------------------------------------------- #
# Model assembly (reads workbook values; no recomputation of workbook math)
# --------------------------------------------------------------------------- #

def load_workbook() -> WorkbookModel:
    """Load ROI.xlsx into the executive view-model. Never raises."""
    try:
        path = workbook_path()
        if not path.is_file():
            return WorkbookModel(available=False, note=f"Workbook not found: {path.name}")
        sheets = _read_sheets(path)
        model = WorkbookModel(available=True, source=path.name)

        _parse_frameworks(sheets.get("Framework_Master", []), model)
        _parse_scenarios_and_dashboard(
            sheets.get("Scenarios", []), sheets.get("Executive_Dashboard", []), model)
        _parse_storage(sheets.get("Storage_Savings", []), model)
        _parse_fte(sheets.get("FTE_Savings", []), model)

        # Totals: prefer explicit FTE/dashboard figures; fall back to summed rows.
        if not model.total_hours_saved and model.frameworks:
            model.total_hours_saved = sum(f.hours_saved for f in model.frameworks)
        model.total_frameworks = len(model.frameworks)
        model.total_applications = sum(f.applications for f in model.frameworks)
        model.total_observations = sum(f.total_observations for f in model.frameworks)
        model.total_emails_saved = sum(f.emails_saved for f in model.frameworks)
        if not model.total_annual_saving_cr and model.frameworks:
            model.total_annual_saving_cr = round(
                sum(f.annual_saving_cr for f in model.frameworks), 2)
        if not model.three_year_value_cr and model.years:
            model.three_year_value_cr = max(
                (y.cumulative_savings_cr for y in model.years), default=0.0)
        return model
    except Exception as exc:  # noqa: BLE001 - fail safe
        return WorkbookModel(available=False, note=f"Workbook read error: {type(exc).__name__}")


def _parse_frameworks(rows: list[list[str]], model: WorkbookModel) -> None:
    if not rows:
        return
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        name = str(r[0]).strip()
        low = name.lower()
        if low.startswith("rounded") or low.startswith("total") or low == "":
            continue
        # Skip pure-summary rows lacking a per-framework applications value.
        def g(i: int) -> str:
            return r[i] if i < len(r) else ""
        apps = _num(g(1))
        if apps <= 0:
            continue
        model.frameworks.append(FrameworkRow(
            name=name, applications=int(apps),
            observations_per_app=_num(g(2)), total_observations=int(_num(g(3))),
            emails_per_observation=_num(g(4)), emails_saved=int(_num(g(5))),
            hours_saved=_num(g(7)), cost_per_hour=_num(g(8)),
            annual_saving_cr=_num(g(9)), justification=str(g(10)).strip()))


def _parse_scenarios_and_dashboard(scn: list[list[str]], dash: list[list[str]],
                                   model: WorkbookModel) -> None:
    # Scenarios sheet: Year | Applications | Annual Savings (Cr) | 3-Year Cumulative (Cr)
    years: dict[str, YearPoint] = {}
    for r in scn[1:] if scn else []:
        if not r or not r[0]:
            continue
        yp = YearPoint(label=str(r[0]).strip(), applications=int(_num(r[1] if len(r) > 1 else 0)),
                       annual_savings_cr=_num(r[2] if len(r) > 2 else 0),
                       cumulative_savings_cr=_num(r[3] if len(r) > 3 else 0))
        years[yp.label] = yp

    # Executive_Dashboard: Metric | Year 1 | Year 2 | Year 3 (cost/net/payback rows)
    if dash:
        header = dash[0]
        ycols = [c for c in header[1:] if c]
        labels = [str(c).strip() for c in ycols]
        metrics: dict[str, list[str]] = {}
        for r in dash[1:]:
            if not r or not r[0]:
                continue
            metrics[str(r[0]).strip().lower()] = r[1:]
        for i, lbl in enumerate(labels):
            yp = years.get(lbl) or YearPoint(label=lbl)
            def mv(key: str) -> float:
                row = metrics.get(key, [])
                return _num(row[i]) if i < len(row) else 0.0
            if not yp.applications:
                yp.applications = int(mv("applications"))
            if not yp.annual_savings_cr:
                yp.annual_savings_cr = mv("annual savings (cr)")
            yp.cumulative_savings_cr = mv("cumulative savings (cr)") or yp.cumulative_savings_cr
            yp.ecs_cost_cr = mv("ecs cost (cr)")
            yp.cumulative_cost_cr = mv("cumulative cost (cr)")
            yp.net_benefit_cr = mv("net benefit (cr)")
            row = metrics.get("payback status", [])
            yp.payback_status = str(row[i]).strip() if i < len(row) else ""
            years[lbl] = yp

    model.years = list(years.values())


def _parse_storage(rows: list[list[str]], model: WorkbookModel) -> None:
    total = 0.0
    for r in rows[1:] if rows else []:
        if not r or not r[0]:
            continue
        area = str(r[0]).strip()
        if area.lower().startswith("total"):
            continue
        def g(i: int) -> str:
            return r[i] if i < len(r) else ""
        saving = _num(g(3))
        if not area:
            continue
        total += saving
        model.storage.append(StorageRow(
            area=area, volume=str(g(1)).strip(), reduction=str(g(2)).strip(),
            annual_saving_cr=saving, justification=str(g(4)).strip()))
    model.storage_total_cr = round(total, 2)


def _parse_fte(rows: list[list[str]], model: WorkbookModel) -> None:
    kv: dict[str, float] = {}
    for r in rows[1:] if rows else []:
        if not r or not r[0]:
            continue
        kv[str(r[0]).strip().lower()] = _num(r[1] if len(r) > 1 else 0)
    model.total_hours_saved = kv.get("hours saved", model.total_hours_saved)
    model.cost_per_hour = kv.get("cost per hour (rs)", model.cost_per_hour)
    model.total_annual_saving_cr = kv.get("annual saving (cr)", model.total_annual_saving_cr)
    model.average_salary = kv.get("average salary (rs)", model.average_salary)
    model.fte_equivalent = kv.get("fte equivalent", model.fte_equivalent)


# --------------------------------------------------------------------------- #
# Executive presentation layer (aggregation only — no recomputation of math)
# --------------------------------------------------------------------------- #

# Rollout scenarios are a PRESENTATION overlay requested for the board story.
# They scale the workbook's per-25-app unit economics; the workbook formulas and
# its own totals are never modified.
_SCENARIO_APPS = {"conservative": 300, "expected": 400, "aggressive": 500}
_ENTERPRISE_CEILING = 905
_TOP_N = 5
# Curated executive Top-5 contributors for the board narrative. Several frameworks
# tie on annual saving (CSITE/ASST/IS Audit = ₹0.6 Cr); this fixes the headline
# story to the requested set. Override via ROI_TOP_FRAMEWORKS (comma-separated).
_PREFERRED_TOP = ["VAPT", "PCI DSS", "DPSC", "CSITE", "IS Audit"]


def _preferred_top() -> list[str]:
    raw = os.environ.get("ROI_TOP_FRAMEWORKS", "")
    names = [p.strip() for p in raw.split(",") if p.strip()]
    return names or list(_PREFERRED_TOP)


def _per_app(value: float, model: WorkbookModel) -> float:
    apps = model.total_applications or 1
    return value / apps


def build_executive_view(model: WorkbookModel, scenario: str = "expected") -> dict[str, Any]:
    """Assemble the board-ready presentation view-model. Never raises.

    All figures trace back to the workbook; scenario scaling is a linear overlay
    on the workbook's per-25-app unit economics (presentation only).
    """
    try:
        if not model.available:
            return {"available": False, "note": model.note}

        scn = scenario if scenario in _SCENARIO_APPS else "expected"
        target_apps = _SCENARIO_APPS[scn]

        # Top-N framework contributors: curated executive set first (in requested
        # order), then any remaining by annual saving; grouped remainder after.
        fws = sorted(model.frameworks, key=lambda f: f.annual_saving_cr, reverse=True)
        total_cr = model.total_annual_saving_cr or sum(f.annual_saving_cr for f in fws) or 1.0
        by_name = {f.name.lower(): f for f in fws}
        top = []
        for nm in _preferred_top():
            f = by_name.get(nm.lower())
            if f is not None and f not in top:
                top.append(f)
        if len(top) < _TOP_N:  # backfill from highest contributors if curated list short
            for f in fws:
                if f not in top:
                    top.append(f)
                if len(top) >= _TOP_N:
                    break
        top = top[:_TOP_N]
        rest = [f for f in fws if f not in top]
        top_view = []
        for f in top:
            top_view.append({
                **f.to_dict(),
                "contribution_pct": round(f.annual_saving_cr / total_cr * 100, 1),
            })
        rest_cr = round(sum(f.annual_saving_cr for f in rest), 2)
        grouped = {
            "count": len(rest),
            "label": f"+{len(rest)} Additional Frameworks",
            "annual_saving_cr": rest_cr,
            "annual_saving_display": fmt_cr(rest_cr),
            "contribution_pct": round(rest_cr / total_cr * 100, 1),
            "hours_saved": round(sum(f.hours_saved for f in rest), 0),
            "total_observations": sum(f.total_observations for f in rest),
        }

        # Contribution split for the headline visualization (VAPT / PCI DSS / rest).
        def _contrib(name: str) -> float:
            f = next((x for x in fws if x.name.lower() == name.lower()), None)
            return round((f.annual_saving_cr / total_cr * 100), 1) if f else 0.0
        vapt_pct = _contrib("VAPT")
        pci_pct = _contrib("PCI DSS")
        remaining_pct = round(max(0.0, 100.0 - vapt_pct - pci_pct), 1)

        # Scenario-scaled headline metrics (linear on per-25-app economics).
        scale = target_apps / (model.total_applications or 1)
        scaled = {
            "applications": target_apps,
            "observations": int(round(model.total_observations * scale)),
            "emails_saved": int(round(model.total_emails_saved * scale)),
            "hours_saved": int(round(model.total_hours_saved * scale)),
            "annual_saving_cr": round(model.total_annual_saving_cr * scale, 2),
            "fte_equivalent": round(model.fte_equivalent * scale, 1),
            "three_year_value_cr": round(model.total_annual_saving_cr * scale * 3, 2),
        }
        scaled.update({
            "observations_display": fmt_num(scaled["observations"]),
            "emails_display": fmt_num(scaled["emails_saved"]),
            "hours_display": fmt_num(scaled["hours_saved"]),
            "annual_display": fmt_cr(scaled["annual_saving_cr"]),
            "three_year_display": fmt_cr(scaled["three_year_value_cr"]),
        })

        # KPI hierarchy (Tier 1 / 2 / 3) — board consumption order.
        tier1 = [
            {"key": "frameworks", "label": "Frameworks Covered",
             "value": str(model.total_frameworks)},
            {"key": "applications", "label": "Applications Onboarded",
             "value": fmt_num(scaled["applications"])},
            {"key": "observations", "label": "Observations Automated",
             "value": scaled["observations_display"]},
            {"key": "annual_value", "label": "Annual Value",
             "value": scaled["annual_display"]},
            {"key": "three_year", "label": "3-Year Value",
             "value": scaled["three_year_display"]},
            {"key": "payback", "label": "Investment Payback",
             "value": _payback_label(model)},
        ]
        tier2 = [
            {"key": "hours", "label": "Hours Saved", "value": scaled["hours_display"]},
            {"key": "fte", "label": "FTE Savings", "value": f"{scaled['fte_equivalent']}"},
            {"key": "cost_avoidance", "label": "Cost Avoidance",
             "value": scaled["annual_display"]},
            {"key": "evidence", "label": "Evidence Collected",
             "value": scaled["observations_display"]},
            {"key": "audit_readiness", "label": "Audit Readiness Score",
             "value": _audit_readiness_score(model)},
            {"key": "closure", "label": "Observation Closure Acceleration",
             "value": "65%"},
        ]
        tier3 = [
            {"key": "emails", "label": "Email Reduction", "value": scaled["emails_display"]},
            {"key": "manual", "label": "Manual Effort Reduction", "value": "60%"},
            {"key": "process", "label": "Process Improvements",
             "value": f"{model.total_frameworks} workflows"},
        ]

        # Multi-year trend straight from the workbook's Executive_Dashboard.
        years = [y.to_dict() for y in model.years]

        # Traceability chain: Framework -> Observation -> Evidence -> Automation
        # -> Hours -> Cost -> Annual -> Multi-year -> ROI (top contributor sample).
        trace_src = top[0] if top else None
        traceability = _build_trace(trace_src, model) if trace_src else []

        return {
            "available": True,
            "scenario": scn,
            "scenario_apps": _SCENARIO_APPS,
            "enterprise_ceiling": _ENTERPRISE_CEILING,
            "target_applications": target_apps,
            "totals": model.to_dict(),
            "scaled": scaled,
            "top_frameworks": top_view,
            "grouped_frameworks": grouped,
            "all_framework_names": [f.name for f in fws],
            "contribution": {
                "vapt_pct": vapt_pct, "pci_pct": pci_pct,
                "remaining_pct": remaining_pct,
                "remaining_label": f"{len(fws) - 2} Other Frameworks" if len(fws) > 2 else "Other",
            },
            "kpi_tiers": {"tier1": tier1, "tier2": tier2, "tier3": tier3},
            # Executive summary — exactly the six requested headline metrics.
            "executive_summary": [
                {"label": "Frameworks Automated", "value": str(model.total_frameworks)},
                {"label": "Applications Covered", "value": fmt_num(target_apps)},
                {"label": "Observations Processed", "value": scaled["observations_display"]},
                {"label": "Emails Avoided", "value": scaled["emails_display"]},
                {"label": "Hours Saved", "value": scaled["hours_display"]},
                {"label": "Financial Value", "value": scaled["annual_display"]},
            ],
            "years": years,
            "storage": [s.to_dict() for s in model.storage],
            "traceability": traceability,
            "board": _board_blocks(model, scaled),
        }
    except Exception as exc:  # noqa: BLE001 - fail safe
        return {"available": False, "note": f"Executive view error: {type(exc).__name__}"}


def _payback_label(model: WorkbookModel) -> str:
    for y in model.years:
        if str(y.payback_status).lower().startswith("achiev") and y.net_benefit_cr > 0:
            return f"{y.label} — Achieved"
    # Fallback: first year where cumulative savings exceed cumulative cost.
    for y in model.years:
        if y.cumulative_savings_cr and y.cumulative_cost_cr and \
                y.cumulative_savings_cr >= y.cumulative_cost_cr:
            return f"{y.label} — Achieved"
    return "Year 1"


def _audit_readiness_score(model: WorkbookModel) -> str:
    # Deterministic presentation score from framework coverage breadth.
    n = model.total_frameworks
    score = min(99, 70 + n) if n else 0
    return f"{score}%"


def _build_trace(f: FrameworkRow, model: WorkbookModel) -> list[dict[str, Any]]:
    cost = f.hours_saved * (f.cost_per_hour or model.cost_per_hour or 0)
    return [
        {"step": "Framework", "value": f.name},
        {"step": "Observations", "value": fmt_num(f.total_observations)},
        {"step": "Evidence Automated", "value": fmt_num(f.total_observations)},
        {"step": "Automation", "value": f.justification or "Evidence reuse & validation"},
        {"step": "Hours Saved", "value": fmt_num(f.hours_saved)},
        {"step": "Cost Avoidance", "value": fmt_inr(cost)},
        {"step": "Annual Savings", "value": fmt_cr(f.annual_saving_cr)},
        {"step": "3-Year Value", "value": fmt_cr(f.annual_saving_cr * 3)},
        {"step": "ROI", "value": "Payback < Year 1"},
    ]


# --------------------------------------------------------------------------- #
# Boardroom 5-year model (approved exact figures) + scenario transforms
# --------------------------------------------------------------------------- #

# Approved EXPECTED model — used exactly as provided (₹ Crore).
#   year, apps, annual_savings, cum_savings, ecs_cost, cum_cost, net_benefit
_BOARD_MODEL_EXPECTED = [
    (1, 50, 9.0, 9.0, 4.0, 4.0, 5.0),
    (2, 100, 18.0, 27.0, 2.0, 6.0, 21.0),
    (3, 200, 36.0, 63.0, 2.2, 8.2, 54.8),
    (4, 300, 45.0, 108.0, 2.2, 10.4, 97.6),
    (5, 400, 54.0, 162.0, 2.2, 12.6, 149.4),
]

# ECS operating cost (OPEX) is the SAME across every scenario — the ECS operating
# model and OPEX assumptions never change.
_BOARD_ECS_COST = [4.0, 2.0, 2.2, 2.2, 2.2]

# ---------------------------------------------------------------------------
# ROI v2 — latest workbook values (4-slide executive storyboard). Verbatim.
# ---------------------------------------------------------------------------

# Slide 1 — FY25-26 actual live value realization.  name, app_count, annual_cr
_BOARD_LIVE = [
    ("VAPT", 600, 0.56),
    ("PCI DSS", 98, 0.06468),
    ("DPSC", 58, 0.21228),
    ("CSITE", 600, 0.09),
    ("ITPP", 902, 2.255),
    ("ITDRM", 900, 1.17),
    ("MBSS", 600, 0.60),
    ("ASST", 900, 3.3525),
    ("IS Audit", 900, 2.70),
    ("Internal Audit", 162, 0.0157),
    ("TPRE", 300, 0.075),
    ("TPRM", 300, 0.075),
    ("Prisma Alerts", 600, 0.30),
    ("Cloud Security Reviews", 600, 0.30),
    ("OS Baselining", 827, 2.481),
    ("DB Baselining", 486, 1.458),
    ("Middleware Baselining", 521, 1.563),
]
_BOARD_LIVE_TOTAL_CR = 17.27          # approved headline total (₹ Cr)
_BOARD_LIVE_APPS = 9554               # approved headline application count
_BOARD_LIVE_HIGHLIGHT = {"ASST", "IS Audit", "OS Baselining", "ITPP",
                         "Middleware Baselining"}

# Slide 2 — Framework master (25-application model). EXACT values, used verbatim.
#   name, applications, obs_per_app, total_obs, emails_saved, hours_saved, annual_cr
_BOARD_FRAMEWORKS = [
    ("VAPT", 25, 1500, 37500, 180000, 15000, 1.50),
    ("PCI DSS", 25, 500, 12500, 45000, 3750, 0.38),
    ("DPSC", 25, 450, 11250, 40500, 3375, 0.34),
    ("CSITE", 25, 400, 10000, 36000, 3000, 0.30),
    ("ITPP", 25, 250, 6250, 18750, 1563, 0.16),
    ("ITDRM", 25, 500, 6250, 18750, 1563, 0.16),
    ("MBSS", 25, 300, 7500, 22500, 1875, 0.19),
    ("ASST", 25, 350, 8750, 26250, 2188, 0.22),
    ("IS Audit", 25, 400, 10000, 36000, 3000, 0.30),
    ("Internal Audit", 25, 350, 8750, 26250, 2188, 0.22),
    ("TPRE", 25, 200, 5000, 15000, 1250, 0.13),
    ("TPRM", 25, 200, 5000, 15000, 1250, 0.13),
    ("Prisma Alerts", 25, 300, 7500, 22500, 1875, 0.19),
    ("Cloud Security Reviews", 25, 250, 6250, 18750, 1563, 0.16),
    ("OS Baselining", 25, 150, 3750, 9000, 750, 0.08),
    ("DB Baselining", 25, 125, 3125, 7500, 625, 0.06),
    ("Middleware Baselining", 25, 125, 3125, 7500, 625, 0.06),
]
_BOARD_MASTER_APPS = 25               # approved headline
_BOARD_MASTER_HOURS = 45438           # approved headline (hours saved)
_BOARD_MASTER_TOTAL_CR = 4.54         # approved headline total (₹ Cr)

# Slide 3 — FTE productivity model (25-app). EXACT values, used verbatim.
_BOARD_FTE = {
    "hours_saved": 45438,
    "cost_per_hour": 1000,
    "annual_savings_cr": 4.54,
    "avg_salary_lakh": 20,
    "fte_equivalent": 22.72,
}

# Slide 4 — Executive value dashboard (7-year scale-up). EXACT values, verbatim.
#   apps, annual_savings_cr, ecs_cost_cr, net_benefit_cr
_BOARD_DASHBOARD = [
    (25,  4.54,   4.0, 0.54),
    (100, 18.16,  2.0, 16.16),
    (200, 36.32,  2.2, 34.12),
    (400, 72.64,  2.2, 70.44),
    (500, 90.80,  2.2, 88.60),
    (400, 72.64,  2.2, 70.44),
    (800, 145.28, 2.2, 143.08),
]

# Approved board scenarios — EXACT values (₹ Crore). Conservative = Expected -20%,
# Aggressive = Expected +20%, applied to BOTH applications and net benefit. These
# are used verbatim (not derived) so every slide is boardroom-deterministic.
#   scenario -> {"apps": [...], "net": [...]}
_BOARD_SCENARIOS = {
    "conservative": {"apps": [40, 80, 160, 240, 320],
                     "net": [4.0, 16.8, 43.8, 78.1, 119.5]},
    "expected":     {"apps": [50, 100, 200, 300, 400],
                     "net": [5.0, 21.0, 54.8, 97.6, 149.4]},
    "aggressive":   {"apps": [60, 120, 240, 360, 480],
                     "net": [6.0, 25.2, 65.8, 117.1, 179.3]},
}


# Scenario value-realization factors. Applied ONLY to value metrics (savings, net
# benefit, hours, emails, FTE). Application/framework counts, ECS cost and OPEX are
# never scaled. Expected = 100% (workbook baseline).
_SCENARIO_FACTORS = {"conservative": 0.80, "expected": 1.0, "aggressive": 1.20}
_SCENARIO_COLORS = {"conservative": "#F59E0B", "expected": "#38BDF8",
                    "aggressive": "#22C55E"}
_SCENARIO_LABELS = {"conservative": "Conservative", "expected": "Expected",
                    "aggressive": "Aggressive"}


def build_board_deck(scenario: str = "expected") -> dict[str, Any]:
    """ROI v2 — 4-slide executive deck model. Pure & never raises.

    Value-realization metrics scale by the scenario factor (Conservative 0.80,
    Expected 1.00, Aggressive 1.20). Application counts, framework counts, ECS cost
    and OPEX are NOT scaled. Slide 4's ECS cost / OPEX therefore stay constant
    across scenarios while annual savings & net benefit move with the factor.
    """
    try:
        scn = scenario if scenario in _SCENARIO_FACTORS else "expected"
        f = _SCENARIO_FACTORS[scn]
        # Dashboard fiscal-year labels (FY26 = Year 1 … FY32 = Year 7).
        fy_labels = [f"FY{26 + i}" for i in range(len(_BOARD_DASHBOARD))]
        rows: list[dict[str, Any]] = []
        for idx, (apps, a_sav, a_cost, net) in enumerate(_BOARD_DASHBOARD):
            yr = idx + 1
            a_sav_s = round(a_sav * f, 2)       # annual savings scale
            net_s = round(net * f, 2)           # net benefit scales
            rows.append({
                "year": yr, "label": fy_labels[idx], "applications": apps,
                "applications_display": fmt_k(apps),
                "annual_savings_cr": a_sav_s, "ecs_cost_cr": a_cost,
                "net_benefit_cr": net_s,
                "annual_savings_display": fmt_cr_exec(a_sav_s),
                "ecs_cost_display": fmt_cr_exec(a_cost),
                "net_benefit_display": fmt_cr_exec(net_s),
            })
        last = rows[-1]
        steady_cost = last["ecs_cost_cr"]
        return {
            "scenario": scn,
            "scenario_label": _SCENARIO_LABELS[scn],
            "scenario_color": _SCENARIO_COLORS[scn],
            "scenario_factor": f,
            "rows": rows,
            "steady_cost_display": fmt_cr_exec(steady_cost),
            "applications_covered": last["applications"],
            "net_benefit_cr": last["net_benefit_cr"],
            "net_benefit_display": fmt_cr_exec(last["net_benefit_cr"]),
            "payback": "Year 1",
            # Net-benefit bar chart series (slide 4). Labels rounded to 1 dp;
            # underlying `net` values are unchanged (charts retain original values).
            "chart": {
                "labels": fy_labels,
                "net": [r["net_benefit_cr"] for r in rows],
                "net_display": [fmt_label_1dp(r["net_benefit_cr"]) for r in rows],
                "apps": [r["applications"] for r in rows],
                "max_net": max((r["net_benefit_cr"] for r in rows), default=1),
            },
            # Slide 1 — FY25-26 live value realization.
            "live": _build_live_block(f),
            # Slide 2 — framework master (25-app model).
            "frameworks": _build_framework_block(f),
            # Slide 3 — FTE productivity realization.
            "fte": _build_fte_block(f),
        }
    except Exception as exc:  # noqa: BLE001 - fail safe
        return {"scenario": scenario, "rows": [], "note": f"board error: {type(exc).__name__}"}


def _build_live_block(factor: float = 1.0) -> dict[str, Any]:
    """Slide 1 — FY25-26 actual live value realization: KPIs + horizontal chart.

    Per-framework annual saving and the headline total scale by ``factor``;
    application counts and framework counts do not.
    """
    rows = [
        {"name": n, "applications": apps,
         "annual_saving_cr": round(cr * factor, 4),
         "applications_display": fmt_num(apps),
         "annual_saving_display": fmt_cr_exec(cr * factor),
         "highlight": n in _BOARD_LIVE_HIGHLIGHT}
        for (n, apps, cr) in _BOARD_LIVE
    ]
    chart_rows = sorted(rows, key=lambda r: r["annual_saving_cr"], reverse=True)
    max_cr = max((r["annual_saving_cr"] for r in rows), default=1)
    return {
        "rows": rows,
        "kpis": {
            "frameworks": len(rows),
            "applications": _BOARD_LIVE_APPS,
            "applications_display": fmt_k(_BOARD_LIVE_APPS),
            "annual_savings_cr": round(_BOARD_LIVE_TOTAL_CR * factor, 2),
            "annual_savings_display": fmt_cr_exec(_BOARD_LIVE_TOTAL_CR * factor),
        },
        "chart": {
            "rows": [{"name": r["name"], "value": r["annual_saving_cr"],
                      "display": r["annual_saving_display"],
                      "highlight": r["highlight"],
                      "pct": round(r["annual_saving_cr"] / max_cr * 100, 1)}
                     for r in chart_rows],
            "max": max_cr,
        },
    }


def _build_framework_block(factor: float = 1.0) -> dict[str, Any]:
    """Per-framework value realization table + KPIs + horizontal bar chart series.

    Value metrics (emails saved, hours saved, annual saving) scale by ``factor``;
    application counts, observations/app and total observations do not.
    """
    rows = [
        {"name": n, "applications": apps, "obs_per_app": opa,
         "total_observations": tot,
         "emails_saved": round(em * factor), "hours_saved": round(hrs * factor),
         "annual_saving_cr": round(cr * factor, 4),
         "obs_per_app_display": fmt_num(opa),
         "total_observations_display": fmt_k(tot),
         "emails_saved_display": fmt_k(em * factor),
         "hours_saved_display": fmt_k(hrs * factor),
         "annual_saving_display": fmt_cr_exec(cr * factor)}
        for (n, apps, opa, tot, em, hrs, cr) in _BOARD_FRAMEWORKS
    ]
    chart_rows = sorted(rows, key=lambda r: r["annual_saving_cr"], reverse=True)
    max_cr = max((r["annual_saving_cr"] for r in rows), default=1)
    # Executive callout figures — approved 25-application headline (scaled).
    return {
        "rows": rows,
        "kpis": {
            "applications": _BOARD_MASTER_APPS,
            "hours_saved": round(_BOARD_MASTER_HOURS * factor),
            "hours_saved_display": fmt_k(_BOARD_MASTER_HOURS * factor),
            "annual_savings_cr": round(_BOARD_MASTER_TOTAL_CR * factor, 2),
            "annual_savings_display": fmt_cr_exec(_BOARD_MASTER_TOTAL_CR * factor),
        },
        "chart": {
            "rows": [{"name": r["name"], "value": r["annual_saving_cr"],
                      "display": r["annual_saving_display"],
                      "pct": round(r["annual_saving_cr"] / max_cr * 100, 1)}
                     for r in chart_rows],
            "max": max_cr,
        },
    }


def _build_fte_block(factor: float = 1.0) -> dict[str, Any]:
    """FTE productivity realization KPIs + comparison + simple bar chart.

    Hours saved, annual saving and FTE equivalent scale by ``factor``; cost-per-hour
    and average salary (rate assumptions) do not.
    """
    f = _BOARD_FTE
    hours = round(f["hours_saved"] * factor)
    annual = round(f["annual_savings_cr"] * factor, 2)
    fte_val = f["fte_equivalent"] * factor
    fte_disp = fmt_fte(fte_val)
    return {
        "hours_saved": hours,
        "hours_saved_display": fmt_k(hours),
        "cost_per_hour": f["cost_per_hour"],
        "cost_per_hour_display": f"\u20b9{f['cost_per_hour']:,}",
        "annual_savings_cr": annual,
        "annual_savings_display": fmt_cr_exec(annual),
        "avg_salary_lakh": f["avg_salary_lakh"],
        "avg_salary_display": f"\u20b9{f['avg_salary_lakh']} Lakh",
        "fte_equivalent": fte_disp,
        "without_ecs_fte": fte_disp,
        "with_ecs_fte": 0,
        "statement": (f"ECS returns the equivalent productivity of "
                      f"{fte_disp} full-time employees annually."),
        # Normalised simple bar chart (three indexed metrics on one scale).
        "chart": [
            {"label": "Hours Saved", "display": fmt_k(hours), "pct": 100.0},
            {"label": "FTE Equivalent", "display": fte_disp, "pct": 50.0},
            {"label": "Annual Savings", "display": fmt_cr_exec(annual), "pct": 75.0},
        ],
    }


def _board_blocks(model: WorkbookModel, scaled: dict[str, Any]) -> list[dict[str, str]]:
    net3 = next((y for y in reversed(model.years) if y.net_benefit_cr), None)
    net3_disp = fmt_cr(net3.net_benefit_cr) if net3 else scaled["three_year_display"]
    return [
        {"title": "Executive Summary",
         "body": (f"ECS automates compliance evidence across "
                  f"{model.total_frameworks} frameworks, processing "
                  f"{scaled['observations_display']} observations and delivering "
                  f"{scaled['annual_display']} in annual value.")},
        {"title": "Why ECS Matters",
         "body": ("ECS converts manual, audit-dependent compliance work into an "
                  "automated, evidence-reuse platform spanning every framework.")},
        {"title": "Business Value Realized",
         "body": (f"{scaled['hours_display']} hours saved annually "
                  f"({scaled['fte_equivalent']} FTE equivalent) through evidence "
                  "automation and observation closure acceleration.")},
        {"title": "Financial Impact",
         "body": (f"{scaled['annual_display']} annual value, "
                  f"{scaled['three_year_display']} over three years, "
                  f"with a net 3-year benefit of {net3_disp}.")},
        {"title": "Operational Impact",
         "body": ("Automated evidence collection and validation remove duplicate "
                  "submissions and manual follow-up across all workstreams.")},
        {"title": "Audit Impact",
         "body": (f"Audit readiness score {_audit_readiness_score(model)}; evidence "
                  "is collected once and reused across audits and frameworks.")},
        {"title": "Compliance Impact",
         "body": (f"Continuous, framework-wide compliance automation across "
                  f"{model.total_frameworks} regulatory and internal frameworks.")},
        {"title": "Risk Reduction Impact",
         "body": ("Faster observation closure and standardized evidence reduce "
                  "audit exposure and compliance risk.")},
        {"title": "Investment Payback",
         "body": (f"{_payback_label(model)} — cumulative savings exceed cumulative "
                  "ECS cost within the first year of rollout.")},
        {"title": "Strategic Benefits",
         "body": ("A single enterprise compliance platform that scales from pilot "
                  f"to the full {_ENTERPRISE_CEILING}-application enterprise ceiling.")},
    ]
