"""Network, per-connector, and DB Agent benchmark estimators (PART 6/7/8).

Estimates:
  * PART 6 — bandwidth: AWS<->GCP cross-cloud, connector ingress, DB Agent,
    evidence upload/download, object-storage, per-SaaS connector.
  * PART 7 — per-connector benchmark: latency, bandwidth, payload, CPU, RAM,
    retry frequency, timeouts, normalization time, evidence generation.
  * PART 8 — DB Agent benchmark: connect time, pooling, query latency, rows,
    evidence generation, normalization, hashing, upload, parallel execution.

Pure arithmetic over documented per-connector/per-unit assumptions x profile.
Reuses the connector registry (``modules.operations.integrations.list_adapters``)
so the connector set stays in sync with the real adapters — no connector list is
hardcoded or duplicated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from benchmarks.capacity.profiles import CapacityProfile

_GIB = 1024 ** 3
_MIB = 1024 ** 2
_KIB = 1024


def _gib(b: float) -> float:
    return round(b / _GIB, 4)


def _round(x: float, n: int = 3) -> float:
    return round(float(x), n)


# Per-connector network/perf profile (documented planning defaults, tunable).
# payload_kb = avg response payload per fetch; latency_ms = avg round-trip;
# cross_cloud = whether traffic typically crosses AWS<->GCP.
_CONNECTOR_PROFILE: dict[str, dict[str, Any]] = {
    "servicenow_cmdb": {"payload_kb": 400, "latency_ms": 350, "cross_cloud": False},
    "archer": {"payload_kb": 300, "latency_ms": 400, "cross_cloud": False},
    "sharepoint_graph": {"payload_kb": 800, "latency_ms": 300, "cross_cloud": False},
    "teams_graph": {"payload_kb": 250, "latency_ms": 300, "cross_cloud": False},
    "outlook_graph": {"payload_kb": 350, "latency_ms": 300, "cross_cloud": False},
    "jira": {"payload_kb": 300, "latency_ms": 250, "cross_cloud": False},
    "confluence": {"payload_kb": 500, "latency_ms": 280, "cross_cloud": False},
    "sonarqube": {"payload_kb": 450, "latency_ms": 220, "cross_cloud": False},
    "checkmarx": {"payload_kb": 400, "latency_ms": 350, "cross_cloud": False},
    "prisma_cloud": {"payload_kb": 600, "latency_ms": 400, "cross_cloud": True},
    "tripwire": {"payload_kb": 350, "latency_ms": 300, "cross_cloud": False},
    "aws_connector": {"payload_kb": 700, "latency_ms": 300, "cross_cloud": True},   # AWS Net Banking
    "azure_connector": {"payload_kb": 600, "latency_ms": 320, "cross_cloud": True},
    "gcp_connector": {"payload_kb": 600, "latency_ms": 150, "cross_cloud": False},  # GCP Mobile Banking
    "nessus": {"payload_kb": 900, "latency_ms": 450, "cross_cloud": False},
    "qualys": {"payload_kb": 900, "latency_ms": 450, "cross_cloud": False},
    "github": {"payload_kb": 400, "latency_ms": 200, "cross_cloud": True},
    "jenkins": {"payload_kb": 350, "latency_ms": 250, "cross_cloud": False},
    "azure_devops": {"payload_kb": 400, "latency_ms": 300, "cross_cloud": True},
}

_DEFAULT_CONNECTOR = {"payload_kb": 400, "latency_ms": 300, "cross_cloud": False}


@dataclass
class NetworkConstants:
    retry_rate: float = 0.05                 # fraction of fetches retried
    timeout_rate: float = 0.01
    normalize_ms_per_kb: float = 0.5         # normalization time per KB payload
    connector_cpu_ms_per_kb: float = 2.0
    connector_ram_mib_per_fetch: float = 48.0
    evidence_per_connector_run: float = 5.0
    avg_api_response_kb: float = 40.0        # evidence upload/download UI payloads
    db_agent_connect_ms: float = 120.0
    db_agent_query_ms: float = 180.0
    db_agent_rows_per_query: int = 500
    db_agent_bytes_per_row: int = 256
    db_agent_hash_ms_per_evidence: float = 15.0
    db_agent_pool_size: int = 10
    db_agent_parallelism: int = 4
    working_days_per_month: int = 22
    months_per_year: int = 12

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _connector_profile(name: str) -> dict[str, Any]:
    return _CONNECTOR_PROFILE.get(name, _DEFAULT_CONNECTOR)


def _adapter_names() -> list[str]:
    """Connector set from the real registry (fallback to the profile keys)."""
    try:
        from modules.operations import integrations
        names = list(integrations.list_adapters())
        # include CI/CD adapters if registered
        return names or list(_CONNECTOR_PROFILE.keys())
    except Exception:  # noqa: BLE001
        return list(_CONNECTOR_PROFILE.keys())


def connector_benchmark(p: CapacityProfile, c: NetworkConstants | None = None) -> dict[str, Any]:
    """Per-connector latency/bandwidth/payload/CPU/RAM/retry/normalize (PART 7)."""
    c = c or NetworkConstants()
    names = _adapter_names()
    # Distribute the profile's daily connector runs across the configured adapters.
    runs_per_connector_day = p.connector_runs_per_day / max(1, len(names))

    per_connector: dict[str, Any] = {}
    for name in names:
        prof = _connector_profile(name)
        payload_kb = float(prof["payload_kb"])
        daily_bytes = runs_per_connector_day * payload_kb * _KIB
        per_connector[name] = {
            "avg_latency_ms": prof["latency_ms"],
            "avg_payload_kb": payload_kb,
            "cross_cloud": bool(prof["cross_cloud"]),
            "runs_per_day": _round(runs_per_connector_day, 1),
            "bandwidth_gib_per_day": _gib(daily_bytes),
            "cpu_ms_per_run": _round(payload_kb * c.connector_cpu_ms_per_kb, 1),
            "ram_mib_per_run": c.connector_ram_mib_per_fetch,
            "retry_rate": c.retry_rate,
            "timeout_rate": c.timeout_rate,
            "normalization_ms": _round(payload_kb * c.normalize_ms_per_kb, 1),
            "evidence_per_run": c.evidence_per_connector_run,
        }
    return {
        "connectors": per_connector,
        "connector_count": len(names),
        "_basis": "Daily runs distributed across registered adapters × per-connector payload/latency.",
    }


def db_agent_benchmark(p: CapacityProfile, c: NetworkConstants | None = None) -> dict[str, Any]:
    """DB Agent connect/pool/query/rows/evidence/normalize/hash/upload/parallel (PART 8)."""
    c = c or NetworkConstants()
    queries_per_day = p.connector_runs_per_day + p.scheduler_jobs_per_day
    bytes_per_query = c.db_agent_rows_per_query * c.db_agent_bytes_per_row
    daily_bytes = queries_per_day * bytes_per_query
    evidence_per_day = queries_per_day * c.evidence_per_connector_run
    return {
        "connect_time_ms": c.db_agent_connect_ms,
        "pool_size": c.db_agent_pool_size,
        "parallelism": c.db_agent_parallelism,
        "query_latency_ms": c.db_agent_query_ms,
        "rows_per_query": c.db_agent_rows_per_query,
        "queries_per_day": int(queries_per_day),
        "result_bandwidth_gib_per_day": _gib(daily_bytes),
        "evidence_generated_per_day": int(evidence_per_day),
        "normalization_ms_per_evidence": _round(c.db_agent_rows_per_query * 0.02, 1),
        "hash_ms_per_evidence": c.db_agent_hash_ms_per_evidence,
        "upload_ms_per_evidence": _round(bytes_per_query / _KIB * 0.5, 1),
        "_basis": "Queries/day × rows × bytes/row; evidence per query; pooled + parallel execution.",
    }


def network_bandwidth(p: CapacityProfile, connectors: dict[str, Any],
                      c: NetworkConstants | None = None) -> dict[str, Any]:
    """Aggregate bandwidth incl. AWS<->GCP cross-cloud (PART 6)."""
    c = c or NetworkConstants()
    per_conn = connectors.get("connectors", {})
    total_conn_gib_day = sum(v["bandwidth_gib_per_day"] for v in per_conn.values())
    cross_cloud_gib_day = sum(v["bandwidth_gib_per_day"] for v in per_conn.values() if v.get("cross_cloud"))

    # Evidence upload/download + object-storage + API traffic.
    api_bytes_day = p.api_requests_per_day * c.avg_api_response_kb * _KIB
    evidence_up_day = p.connector_runs_per_day * c.evidence_per_connector_run * p.avg_evidence_size_kb * _KIB
    # Downloads: assume ~30% of stored evidence viewed/exported over a day at scale.
    evidence_down_day = evidence_up_day * 0.3
    object_storage_day = evidence_up_day + evidence_down_day

    return {
        "connector_ingress_gib_per_day": _round(total_conn_gib_day, 4),
        "cross_cloud_aws_gcp_gib_per_day": _round(cross_cloud_gib_day, 4),
        "cross_cloud_aws_gcp_gib_per_month": _round(cross_cloud_gib_day * c.working_days_per_month, 3),
        "db_agent_gib_per_day": db_agent_benchmark(p, c)["result_bandwidth_gib_per_day"],
        "evidence_upload_gib_per_day": _gib(evidence_up_day),
        "evidence_download_gib_per_day": _gib(evidence_down_day),
        "object_storage_gib_per_day": _gib(object_storage_day),
        "api_traffic_gib_per_day": _gib(api_bytes_day),
        "total_egress_estimate_gib_per_month": _round(
            (total_conn_gib_day + _gib(object_storage_day) + _gib(api_bytes_day))
            * c.working_days_per_month, 3),
        "_basis": "Per-connector payloads (cross-cloud flagged) + evidence up/down + API traffic.",
    }
