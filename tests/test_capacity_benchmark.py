"""Tests for the ECS GCP/GKE capacity-sizing benchmark.

Covers: profile loading, storage estimation, CPU/RAM estimation, token-benchmark
integration (reuses the ECS token estimator), report generation (JSON/MD/CSV),
and the CLI dry-run. Pure/offline.
"""

from __future__ import annotations

import json

import pytest

from benchmarks.capacity import (
    SizingConstants,
    estimate_capacity,
    get_profile,
    list_profiles,
)
from benchmarks.capacity import report as rpt
from benchmarks.capacity.profiles import PROFILES, CapacityProfile


# --------------------------------------------------------------------------- #
# Profile loading
# --------------------------------------------------------------------------- #
def test_all_expected_profiles_exist():
    keys = list_profiles()
    for expected in ["demo", "phase1", "phase2", "enterprise", "pan-bank", "large"]:
        assert expected in keys


def test_get_profile_and_totals():
    p = get_profile("phase1")
    assert isinstance(p, CapacityProfile)
    assert p.total_controls() == p.apps * p.controls_per_app
    assert p.total_evidences() == p.apps * p.evidences_per_app
    d = p.to_dict()
    assert d["total_controls"] == p.total_controls()


def test_get_profile_unknown_raises():
    with pytest.raises(KeyError):
        get_profile("nope")


def test_profiles_scale_monotonically():
    # apps should be non-decreasing across the ordered profiles.
    apps = [PROFILES[k].apps for k in list_profiles()]
    assert apps == sorted(apps)
    assert apps[0] == 1 and apps[-1] == 2000   # laptop (1) .. large (2000)


# --------------------------------------------------------------------------- #
# Estimation shape
# --------------------------------------------------------------------------- #
def test_estimate_has_all_sections():
    est = estimate_capacity(get_profile("phase1"))
    for section in ("profile", "token_feed", "gke_compute", "node_pool",
                    "postgres_pgvector", "gcs_object_storage",
                    "logging_monitoring", "constants", "_meta"):
        assert section in est, f"missing {section}"
    assert est["_meta"]["kind"] == "gcp_capacity_estimate"


# --------------------------------------------------------------------------- #
# CPU / RAM estimation
# --------------------------------------------------------------------------- #
def test_gke_compute_positive_and_replicas_floor():
    est = estimate_capacity(get_profile("phase1"))
    gke = est["gke_compute"]
    assert gke["peak_cores"] > 0
    assert gke["peak_ram_mib"] > 0
    assert gke["recommended_replicas"] >= 2   # HA floor
    assert gke["recommended_pod"]["cpu_request"].endswith("m")


def test_replicas_and_nodes_grow_with_scale():
    small = estimate_capacity(get_profile("phase1"))
    big = estimate_capacity(get_profile("large"))
    assert big["gke_compute"]["recommended_replicas"] > small["gke_compute"]["recommended_replicas"]
    assert big["node_pool"]["recommended_nodes"] >= small["node_pool"]["recommended_nodes"]


def test_more_prompt_runs_increase_cpu():
    base = get_profile("enterprise")
    est_low = estimate_capacity(base)
    # Double prompt runs -> more prompt CPU core-hours.
    from dataclasses import replace
    est_high = estimate_capacity(replace(base, prompt_runs_per_day=base.prompt_runs_per_day * 2))
    assert (est_high["gke_compute"]["daily_cpu_core_hours"]["prompts"]
            > est_low["gke_compute"]["daily_cpu_core_hours"]["prompts"])


# --------------------------------------------------------------------------- #
# Storage estimation
# --------------------------------------------------------------------------- #
def test_storage_grows_with_apps():
    small = estimate_capacity(get_profile("phase1"))
    big = estimate_capacity(get_profile("enterprise"))
    assert (big["postgres_pgvector"]["storage_gib"]["year_1_total"]
            > small["postgres_pgvector"]["storage_gib"]["year_1_total"])
    assert (big["gcs_object_storage"]["year_1_total_gib"]
            > small["gcs_object_storage"]["year_1_total_gib"])


def test_year5_exceeds_year1():
    est = estimate_capacity(get_profile("enterprise"))
    pg = est["postgres_pgvector"]["storage_gib"]
    gcs = est["gcs_object_storage"]
    assert pg["year_5_total"] >= pg["year_1_total"]
    assert gcs["year_5_total_gib"] >= gcs["year_1_total_gib"]


def test_cloud_sql_tier_bumps_at_scale():
    small = estimate_capacity(get_profile("demo"))["postgres_pgvector"]["recommended_cloud_sql"]
    big = estimate_capacity(get_profile("large"))["postgres_pgvector"]["recommended_cloud_sql"]
    assert big["vcpu"] >= small["vcpu"]


def test_vector_storage_uses_embedding_dimensions():
    c = SizingConstants()
    est = estimate_capacity(get_profile("phase1"), constants=c)
    vec = est["postgres_pgvector"]["vectors"]
    assert vec["embedding_dimensions"] == c.embedding_dimensions
    # bytes/chunk = dims * 4 * 1.3
    expected = c.embedding_dimensions * c.bytes_per_dimension * c.vector_index_overhead_factor
    assert abs(vec["bytes_per_chunk"] - round(expected, 1)) < 0.5


def test_logging_volume_positive_and_components():
    logs = estimate_capacity(get_profile("phase1"))["logging_monitoring"]
    per_day = logs["per_day_gib"]
    for k in ("application", "connector", "scheduler", "llm_execution", "audit_trail", "total"):
        assert k in per_day
    assert logs["per_year_gib"] >= logs["per_day_gib"]["total"]


# --------------------------------------------------------------------------- #
# Token benchmark integration (reuses the ECS token estimator)
# --------------------------------------------------------------------------- #
def test_token_feed_estimated_by_default():
    est = estimate_capacity(get_profile("phase1"))
    tf = est["token_feed"]
    assert tf["total"] > 0
    assert "estimated" in tf["_source"] or tf["_source"] in ("fallback",)


def test_token_feed_uses_measured_when_supplied():
    measured = {"avg_input_tokens": 1000, "avg_output_tokens": 400, "avg_total_tokens": 1400}
    est = estimate_capacity(get_profile("phase1"), measured_tokens=measured)
    tf = est["token_feed"]
    assert tf["_source"] == "measured"
    assert tf["total"] == 1400


def test_constants_overridable():
    c = SizingConstants.from_overrides({"cpu_ms_per_api_request": 999.0})
    assert c.cpu_ms_per_api_request == 999.0
    est = estimate_capacity(get_profile("phase1"), constants=c)
    assert est["gke_compute"]["per_unit_cpu_ms"]["api_request"] == 999.0


# --------------------------------------------------------------------------- #
# Report generation
# --------------------------------------------------------------------------- #
def test_json_report_valid():
    ests = [estimate_capacity(get_profile("phase1"))]
    payload = json.loads(rpt.to_json(ests))
    assert payload["report"] == "ecs_gcp_capacity_benchmark"
    assert payload["profiles"] == ["phase1"]
    assert len(payload["recommendation_table"]) == 1


def test_csv_report_has_header_and_rows():
    ests = [estimate_capacity(get_profile(k)) for k in ("phase1", "enterprise")]
    csv_text = rpt.to_csv(ests)
    lines = [l for l in csv_text.splitlines() if l.strip()]
    assert len(lines) == 3  # header + 2 rows
    assert lines[0].startswith("profile,name,apps")


def test_markdown_report_has_table_and_provenance():
    ests = [estimate_capacity(get_profile("phase1"))]
    md = rpt.to_markdown(ests)
    assert "# ECS GCP Capacity Sizing Report" in md
    assert "Provenance" in md
    assert "Recommendation summary" in md
    assert "| Profile |" in md


def test_recommendation_row_keys():
    row = rpt.recommendation_row(estimate_capacity(get_profile("phase1")))
    for k in ("profile", "replicas", "gke_nodes", "cloud_sql_tier",
              "db_year1_gib", "gcs_year1_gib", "logs_per_day_gib"):
        assert k in row


def test_write_reports(tmp_path):
    ests = [estimate_capacity(get_profile("phase1"))]
    paths = rpt.write_reports(ests, str(tmp_path), basename="cap")
    for kind in ("json", "markdown", "csv"):
        assert paths[kind].endswith(("cap.json", "cap.md", "cap.csv"))
        with open(paths[kind]) as fh:
            assert fh.read().strip()


# --------------------------------------------------------------------------- #
# CLI dry-run
# --------------------------------------------------------------------------- #
def test_cli_list(capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "phase1" in out and "enterprise" in out


def test_cli_dry_run_writes_nothing(tmp_path, capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "phase1", "--dry-run", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "dry-run" in out
    assert not list(tmp_path.iterdir())   # nothing written


def test_cli_all_writes_reports(tmp_path, capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--all", "--out", str(tmp_path)])
    assert rc == 0
    written = {p.name for p in tmp_path.iterdir()}
    assert {"capacity.json", "capacity.md", "capacity.csv"} <= written


def test_cli_unknown_profile_errors(tmp_path, capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "does_not_exist", "--out", str(tmp_path)])
    assert rc == 2


# =========================================================================== #
# Enterprise infrastructure benchmark extensions
# =========================================================================== #

# ---- Profiles: all 11 requested scales present ----
def test_all_requested_profiles_present():
    keys = list_profiles()
    for expected in ["laptop", "demo", "pilot", "phase1", "apps25", "apps50",
                     "enterprise", "apps250", "pan-bank", "apps1000", "large"]:
        assert expected in keys, f"missing profile {expected}"


def test_profiles_apps_are_ordered():
    apps = [PROFILES[k].apps for k in list_profiles()]
    assert apps == sorted(apps)


# ---- CPU breakdown (PART 2) ----
def test_cpu_breakdown_covers_operations():
    from benchmarks.capacity import cpu_breakdown
    cpu = cpu_breakdown(get_profile("enterprise"))
    ops = cpu["per_operation_core_hours_per_day"]
    for op in ("rest_api", "authentication", "authorization", "connector_parse",
               "evidence_normalize", "sha256_hash", "evidence_validate",
               "scheduler_dispatch", "retry_queue", "dead_letter_queue",
               "db_query", "prompt_execute", "embedding_generate", "vector_search",
               "json_parse", "csv_parse", "excel_parse", "pdf_parse",
               "zip_generate", "compression", "report_generate", "health_checks"):
        assert op in ops, f"CPU op missing: {op}"
    assert cpu["peak_cores"] > 0


def test_cpu_scales_with_activity():
    from dataclasses import replace
    from benchmarks.capacity import cpu_breakdown
    base = get_profile("enterprise")
    low = cpu_breakdown(base)["total_core_hours_per_day"]
    high = cpu_breakdown(replace(base, api_requests_per_day=base.api_requests_per_day * 4))["total_core_hours_per_day"]
    assert high > low


# ---- RAM breakdown (PART 3) ----
def test_ram_breakdown_consumers_and_hwm():
    from benchmarks.capacity import ram_breakdown
    ram = ram_breakdown(get_profile("enterprise"))
    cons = ram["per_consumer_peak_mib"]
    for k in ("api_requests", "connector_runs", "prompt_context", "db_pools",
              "concurrent_uploads", "caches", "large_object_headroom"):
        assert k in cons
    assert ram["high_water_mark_mib"] >= ram["peak_total_mib"]


# ---- Database durability (PART 4) ----
def test_db_durability_fields():
    from benchmarks.capacity import db_durability
    dur = db_durability(get_profile("enterprise"), base_year1_gib=10.0)
    assert dur["wal_gib_per_day"] >= 0
    assert dur["backup"]["full_backup_gib"] >= 0
    assert dur["backup"]["restore_working_gib"] >= dur["backup"]["full_backup_gib"]
    assert "monthly" in dur["partitioning"]["strategy"]


# ---- Object storage detail (PART 5) ----
def test_object_storage_detail_distribution_and_retention():
    from benchmarks.capacity import object_storage_detail
    det = object_storage_detail(get_profile("enterprise"), base_year1_gib=50.0)
    dist = det["size_distribution"]
    assert dist["p95_kb"] > dist["average_kb"] > dist["median_kb"]
    assert dist["max_kb"] >= dist["p95_kb"]
    ret = det["retention_projection_gib"]
    for yr in ("1_year_gib", "3_year_gib", "5_year_gib", "7_year_gib", "10_year_gib"):
        assert yr in ret
    assert ret["10_year_gib"] >= ret["1_year_gib"]
    assert det["bucket_layout"]["bucket_count"] >= 1
    # content types
    assert "pdf" in det["content_type_breakdown"]


# ---- Network + connector + DB agent (PART 6/7/8) ----
def test_connector_benchmark_covers_registry():
    from benchmarks.capacity import connector_benchmark
    cb = connector_benchmark(get_profile("enterprise"))
    assert cb["connector_count"] >= 15
    # each connector has the required perf fields
    any_conn = next(iter(cb["connectors"].values()))
    for f in ("avg_latency_ms", "avg_payload_kb", "bandwidth_gib_per_day",
              "cpu_ms_per_run", "ram_mib_per_run", "retry_rate", "normalization_ms",
              "evidence_per_run"):
        assert f in any_conn


def test_db_agent_benchmark_fields():
    from benchmarks.capacity import db_agent_benchmark
    a = db_agent_benchmark(get_profile("enterprise"))
    for f in ("connect_time_ms", "pool_size", "parallelism", "query_latency_ms",
              "rows_per_query", "queries_per_day", "evidence_generated_per_day",
              "hash_ms_per_evidence", "upload_ms_per_evidence"):
        assert f in a


def test_network_cross_cloud_present():
    from benchmarks.capacity import connector_benchmark, network_bandwidth
    p = get_profile("enterprise")
    net = network_bandwidth(p, connector_benchmark(p))
    assert net["cross_cloud_aws_gcp_gib_per_day"] >= 0
    assert net["cross_cloud_aws_gcp_gib_per_month"] >= net["cross_cloud_aws_gcp_gib_per_day"]
    assert net["total_egress_estimate_gib_per_month"] > 0


# ---- Cost (PART 13) ----
def test_cost_estimation_structure():
    est = estimate_capacity(get_profile("enterprise"))
    cost = est["cost"]
    mb = cost["monthly_breakdown"]
    for comp in ("compute", "cloud_sql", "object_storage", "logging",
                 "monitoring", "network_egress", "load_balancer"):
        assert comp in mb
    assert cost["monthly_total"] > 0
    assert cost["annual_total"] == round(cost["monthly_total"] * 12, 2)
    assert len(cost["growth_curve"]) == 5
    assert cost["five_year_total"] > cost["annual_total"]


def test_cost_rates_overridable():
    from benchmarks.capacity import CostRates, estimate_cost
    est = estimate_capacity(get_profile("phase1"))
    cheap = estimate_cost(est, CostRates.from_overrides({"cost_per_vcpu_hour": 0.0,
                                                         "sql_cost_per_vcpu_hour": 0.0}))
    dear = estimate_cost(est, CostRates.from_overrides({"cost_per_vcpu_hour": 1.0,
                                                        "sql_cost_per_vcpu_hour": 1.0}))
    assert dear["monthly_total"] > cheap["monthly_total"]


# ---- Full estimate has all extended sections ----
def test_estimate_has_extended_sections():
    est = estimate_capacity(get_profile("phase1"))
    for section in ("cpu_breakdown", "ram_breakdown", "db_durability",
                    "object_storage_detail", "connector_benchmark",
                    "db_agent_benchmark", "network", "cost"):
        assert section in est, f"missing extended section {section}"


# ---- New report types ----
def test_section_reports_generate():
    from benchmarks.capacity import report as r
    ests = [estimate_capacity(get_profile("phase1"))]
    for name, gen in r.SECTION_REPORTS.items():
        md = gen(ests)
        assert md.strip(), f"empty {name} report"
        assert "#" in md


def test_recommendation_row_has_cost():
    from benchmarks.capacity import report as r
    row = r.recommendation_row(estimate_capacity(get_profile("phase1")))
    assert "cost_monthly" in row and "cost_5yr" in row


def test_write_reports_includes_sections(tmp_path):
    from benchmarks.capacity import report as r
    ests = [estimate_capacity(get_profile("phase1"))]
    paths = r.write_reports(ests, str(tmp_path), basename="cap")
    written = {p.name for p in tmp_path.iterdir()}
    for name in ("cap_cpu.md", "cap_ram.md", "cap_storage.md", "cap_database.md",
                 "cap_network.md", "cap_cost.md", "cap_executive.md"):
        assert name in written


# ---- CLI section flags ----
@pytest.mark.parametrize("flag", ["--cpu", "--ram", "--database", "--network", "--storage", "--cost"])
def test_cli_section_flags(flag, tmp_path, capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "phase1", flag])
    out = capsys.readouterr().out
    assert rc == 0
    assert "#" in out   # printed a markdown report


# =========================================================================== #
# Advanced extension: telemetry / kubernetes / stress / calibration /
# throughput / AI / executive
# =========================================================================== #

# ---- Runtime telemetry (PART 1) ----
def test_telemetry_context_manager_and_json():
    import json
    from benchmarks.capacity.telemetry import RuntimeTelemetry, telemetry_availability
    with RuntimeTelemetry("unit", trace_python_heap=True) as t:
        t.add_step("mid")
        _ = sum(range(50000))
    r = t.result
    assert r["name"] == "unit"
    assert "available" in r and isinstance(r["available"], dict)
    assert r["wall_clock_s"] >= 0
    assert any(s["label"] == "mid" for s in r["steps"])
    # Must be JSON-serializable.
    json.dumps(r, default=str)
    assert set(telemetry_availability().keys()) == {"psutil", "resource", "tracemalloc"}


def test_telemetry_never_raises_on_exception():
    from benchmarks.capacity.telemetry import RuntimeTelemetry
    # Telemetry must not suppress the exception, and must still record data.
    t = RuntimeTelemetry("err")
    with pytest.raises(ValueError):
        with t:
            raise ValueError("boom")
    assert t.result.get("error") == "ValueError"


# ---- Kubernetes recommendations (PART 2) ----
def test_kubernetes_recommendation_model():
    from benchmarks.capacity import kubernetes_recommend
    est = estimate_capacity(get_profile("enterprise"))
    k = kubernetes_recommend(est)
    assert k["workload"]["replicas"] >= 2
    assert k["workload"]["pod_requests"]["cpu"].endswith("m")
    assert k["hpa"]["min_replicas"] <= k["hpa"]["max_replicas"]
    assert k["pod_disruption_budget"]["min_available"] >= 1
    assert k["cluster_autoscaler"]["max_nodes"] >= k["cluster_autoscaler"]["min_nodes"]
    assert "eviction_risk" in k
    # also wired into estimate
    assert "kubernetes" in est


# ---- Stress scenarios (PART 3) ----
def test_stress_scenarios_listed_and_generated():
    from benchmarks.capacity import list_scenarios, run_scenario
    scenarios = list_scenarios()
    assert "connector_storm" in scenarios
    assert "sim_1000_connectors" in scenarios
    assert len(scenarios) >= 12
    sc = run_scenario(get_profile("enterprise"), "connector_storm")
    assert sc["impact"]["cpu"]["impact_factor"] >= 1.0
    assert sc["expected_bottleneck"] and sc["recommended_mitigation"]
    for dim in ("cpu", "ram", "network", "storage", "queue"):
        assert dim in sc["impact"]


def test_stress_unknown_scenario():
    from benchmarks.capacity import run_scenario
    r = run_scenario(get_profile("phase1"), "nope")
    assert r.get("error") == "unknown_scenario"


def test_stress_run_all():
    from benchmarks.capacity import stress_run_all
    allr = stress_run_all(get_profile("phase1"))
    assert len(allr["scenarios"]) >= 12


# ---- Calibration (PART 4) ----
def test_calibration_factor_calculation():
    from benchmarks.capacity import calibrate
    rep = calibrate(get_profile("phase1"),
                    {"observed_cpu_cores": 2.0, "observed_ram_mib": 1500,
                     "observed_evidence_size_kb": 300})
    assert rep["applied"] is False
    entries = {e["metric"]: e for e in rep["calibration"]}
    assert "peak_cpu_cores" in entries
    cpu = entries["peak_cpu_cores"]
    # factor = observed / old_estimate; recommended = current_constant * factor
    assert cpu["calibration_factor"] is not None
    assert cpu["recommended_new_constant"] is not None
    assert cpu["confidence"] in ("medium", "low", "very_low")


def test_calibration_empty_observed_is_safe():
    from benchmarks.capacity import calibrate
    rep = calibrate(get_profile("phase1"), {})
    assert rep["calibration"] == []
    assert rep["overall_calibration_factor"] is None


# ---- Object storage throughput (PART 5) ----
def test_object_storage_throughput():
    est = estimate_capacity(get_profile("enterprise"))
    tp = est["object_storage_detail"]["throughput"]
    for k in ("upload_latency_ms_avg", "download_latency_ms_avg",
              "peak_concurrent_uploads", "peak_concurrent_downloads",
              "workload_profile", "multipart_upload_recommended",
              "object_operations_per_month", "gcs_operation_cost_per_month"):
        assert k in tp
    assert tp["upload_latency_ms_avg"] > 0


# ---- Database performance (PART 6) ----
def test_database_performance():
    est = estimate_capacity(get_profile("enterprise"))
    perf = est["db_durability"]["performance"]
    for k in ("queries_per_second_avg", "queries_per_second_peak",
              "transactions_per_second_peak", "recommended_connection_pool",
              "slow_query_risk", "cloud_sql_vcpu_refined_min"):
        assert k in perf
    assert perf["queries_per_second_peak"] >= perf["queries_per_second_avg"]
    assert "restore_time_minutes_est" in est["db_durability"]["backup"]


# ---- AI throughput (PART 7) ----
def test_ai_throughput():
    est = estimate_capacity(get_profile("enterprise"))
    ai = est["ai_throughput"]
    for k in ("prompts_per_second_single_stream", "tokens_per_second_local",
              "embeddings_per_second", "concurrent_capacity",
              "context_window_scaling", "local_ollama_ram_warning",
              "remote_gemini_assumptions"):
        assert k in ai
    cc = ai["concurrent_capacity"]
    assert "local_16gb" in cc and "local_20gb" in cc and "server_gpu_pool" in cc


def test_ai_throughput_uses_measured_tokens():
    from benchmarks.capacity import ai_throughput
    est = estimate_capacity(get_profile("phase1"),
                            measured_tokens={"avg_input_tokens": 1000,
                                             "avg_output_tokens": 500,
                                             "avg_total_tokens": 1500})
    ai = ai_throughput(get_profile("phase1"), est)
    assert ai["avg_tokens_per_prompt"] == 1500.0


# ---- Executive report (PART 8) ----
def test_executive_report_markdown_json_csv():
    import json
    from benchmarks.capacity import executive
    ests = [estimate_capacity(get_profile(k)) for k in ("demo", "phase1", "enterprise")]
    md = executive.to_markdown(ests)
    assert "Executive Capacity Planner" in md
    assert "Top 5 bottlenecks" in md and "Top 5 risks" in md and "Top 5 cost optimizations" in md
    data = json.loads(executive.to_json(ests))
    assert data["report"] == "ecs_executive_capacity_planner"
    assert len(data["top_bottlenecks"]) <= 5 and data["top_bottlenecks"]
    csv_text = executive.to_csv(ests)
    assert csv_text.splitlines()[0].startswith("profile,name,apps")


def test_executive_html_and_write(tmp_path):
    from benchmarks.capacity import executive
    ests = [estimate_capacity(get_profile("phase1"))]
    html = executive.to_html(ests)
    assert "<html" in html and "Executive Capacity Planner" in html
    paths = executive.write_executive(ests, str(tmp_path), html=True)
    written = {p.name for p in tmp_path.iterdir()}
    for f in ("executive.md", "executive.json", "executive.csv", "executive.html"):
        assert f in written


# ---- New CLI flags ----
def test_cli_kubernetes_flag(capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "phase1", "--kubernetes", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0 and "Kubernetes/GKE" in out


def test_cli_stress_flag(capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "phase1", "--stress", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0 and "Stress" in out


def test_cli_stress_scenario_flag(capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "phase1", "--stress-scenario", "connector_storm"])
    out = capsys.readouterr().out
    assert rc == 0 and "connector_storm" in out


def test_cli_telemetry_flag(capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--profile", "phase1", "--telemetry", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0 and "runtime telemetry" in out


def test_cli_executive_flag_writes(tmp_path, capsys):
    from scripts.benchmark_capacity import main
    rc = main(["--all", "--executive", "--html", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0 and "Executive Capacity Planner" in out
    written = {p.name for p in tmp_path.iterdir()}
    assert "executive.md" in written and "executive.html" in written


def test_cli_calibrate_flag(tmp_path, capsys):
    import json
    from scripts.benchmark_capacity import main
    obs = tmp_path / "observed.json"
    obs.write_text(json.dumps({"observed_cpu_cores": 1.0, "observed_ram_mib": 800}))
    rc = main(["--calibrate", str(obs), "--profile", "phase1"])
    out = capsys.readouterr().out
    assert rc == 0 and "calibration" in out
