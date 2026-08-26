"""EAR/EIT onboarding-time demo fixtures — mock evidence, no live connectivity.

Reuses the existing onboarding -> Common-Control evaluation pipeline
end to end (:func:`modules.operations.engines.common_control_onboarding.
onboard_application`) — the rule engine, normalizer, report builder and FCM
mapping are all unmodified. The only thing this module supplies is a mock
:data:`~modules.operations.engines.common_control_evaluation_engine.Executor`:
per the prototype's explicit "mock config/evidence, no live bank
connectivity" requirement, none of the underlying database/NGINX connectors
are ever contacted during this demo path.

Every predefined_query_id referenced below is an EXISTING, already-executable
Phase-1 control (PGX-001, YBX-008, MYX-001, MYX-002, NGX-003, NGX-004) plus
the four CloudKMS controls (CLE-*) registered alongside the rule pack — no
new evaluation logic, verdict vocabulary, or control lives here; this module
only fabricates the connector *output text* those existing controls would
have produced against a real target, then hands it to the same
``complete_connector_execution`` helper every real connector already uses,
so evidence persistence/versioning/audit-trail is fully reused too.

Deterministic verdict story this produces (see tests/test_ear_eit_onboarding_demo.py):

  * Net Banking      (AWS,  Aurora MySQL + NGINX)              -> EAR IMPLEMENTED, EIT IMPLEMENTED
  * Mobile Banking   (GCP,  YugabyteDB + PostgreSQL + NGINX)   -> EAR IMPLEMENTED, EIT PARTIAL
  * Payments         (GCP,  MySQL + NGINX)                      -> EAR NOT_IMPLEMENTED, EIT IMPLEMENTED

Mobile Banking's PARTIAL comes from YugabyteDB SSL being mocked "off" while
PostgreSQL and NGINX are mocked "on" — demonstrating that NGINX TLS being
healthy never masks a failing database TLS check (each technology is
evaluated and aggregated independently; see
common_control_rule_engine.aggregate_verdicts).
"""

from __future__ import annotations

from typing import Any, Callable

DEMO_APP_IDS: tuple[str, ...] = (
    "net_banking_ear_eit_demo",
    "mobile_banking_ear_eit_demo",
    "payments_ear_eit_demo",
)

#: A standalone portfolio dict — deliberately NOT merged into
#: ``config/phase2_application_portfolio.yaml``. That shared file is iterated
#: by other code paths with a REAL executor (scheduler_module.py's reusable
#: Common-Control block, phase2_reusability's own full-portfolio tests); if
#: these demo apps lived there, every real-executor pass over the full
#: portfolio would try to open genuine socket connections for their
#: PostgreSQL/YugabyteDB/Aurora-MySQL-shaped assets and hang on connect
#: timeouts. Passed explicitly via ``portfolio=`` to
#: :func:`~modules.operations.engines.common_control_onboarding.
#: onboard_application`, which already supports an override portfolio for
#: exactly this reason — reused, not a parallel loader.
DEMO_PORTFOLIO: dict[str, Any] = {
    "applications": [
        {
            "id": "net_banking_ear_eit_demo",
            "display_name": "Net Banking (EAR/EIT Demo)",
            "environment": "UAT",
            "cloud": "AWS",
            "technologies": ["aurora_mysql", "nginx"],
            "assets": [
                {"asset_id": "nb-demo-aurora-mysql", "technology": "aurora_mysql"},
                {"asset_id": "nb-demo-nginx", "technology": "nginx"},
            ],
        },
        {
            "id": "mobile_banking_ear_eit_demo",
            "display_name": "Mobile Banking (EAR/EIT Demo)",
            "environment": "UAT",
            "cloud": "GCP",
            "technologies": ["yugabyte", "postgresql", "aerospike", "nginx"],
            "assets": [
                {"asset_id": "mb-demo-yugabyte", "technology": "yugabyte"},
                {"asset_id": "mb-demo-postgresql", "technology": "postgresql"},
                {"asset_id": "mb-demo-aerospike", "technology": "aerospike"},
                {"asset_id": "mb-demo-nginx", "technology": "nginx"},
            ],
        },
        {
            "id": "payments_ear_eit_demo",
            "display_name": "Payments (EAR/EIT Demo)",
            "environment": "UAT",
            "cloud": "GCP",
            "technologies": ["gcp_cloud_sql_mysql", "nginx"],
            "assets": [
                {"asset_id": "pay-demo-mysql", "technology": "gcp_cloud_sql_mysql"},
                {"asset_id": "pay-demo-nginx", "technology": "nginx"},
            ],
        },
    ]
}

#: Mock connector *output text* per application, keyed by the EXISTING
#: predefined_query_id each rule already references. An app only needs
#: entries for the predefined queries its own assets' rules touch.
_DEMO_MOCK_OUTPUTS: dict[str, dict[str, str]] = {
    "net_banking_ear_eit_demo": {
        # Aurora MySQL EIT (technology dispatch owned by MYX-001/002 already).
        "MYX-001": "Variable_name | Value\n----------------------\nhave_ssl | YES",
        "MYX-002": "Variable_name | Value\n----------------------\nrequire_secure_transport | ON",
        # NGINX EIT (shared shape across all three apps).
        "NGX-003": "ssl_protocols TLSv1.2 TLSv1.3;",
        "NGX-004": "ssl_ciphers HIGH:!MEDIUM;",
        # Aurora MySQL EAR (AWS KMS — mock true).
        "CLE-AWS-AURORA-EAR": "name | value\n-----\nencryption_at_rest_enabled | true",
    },
    "mobile_banking_ear_eit_demo": {
        # PostgreSQL EIT — SSL on.
        "PGX-001": "ssl\n---\non",
        # YugabyteDB EIT — SSL off (deliberately, to produce the PARTIAL verdict).
        "YBX-008": "ssl\n---\noff",
        "NGX-003": "ssl_protocols TLSv1.2 TLSv1.3;",
        "NGX-004": "ssl_ciphers HIGH:!MEDIUM;",
        # PostgreSQL + YugabyteDB EAR (GCP CMEK — both mock true).
        "CLE-GCP-POSTGRESQL-EAR": "name | value\n-----\nencryption_at_rest_enabled | true",
        "CLE-GCP-YUGABYTE-EAR": "name | value\n-----\nencryption_at_rest_enabled | true",
    },
    "payments_ear_eit_demo": {
        # MySQL EIT reuses the Aurora MySQL PQs (rule technology="MySQL" is
        # independent of the PQ's own execution-dispatch technology).
        "MYX-001": "Variable_name | Value\n----------------------\nhave_ssl | YES",
        "MYX-002": "Variable_name | Value\n----------------------\nrequire_secure_transport | ON",
        "NGX-003": "ssl_protocols TLSv1.2 TLSv1.3;",
        "NGX-004": "ssl_ciphers HIGH:!MEDIUM;",
        # MySQL EAR (GCP default-key disk encryption, not CMEK — mock false).
        "CLE-GCP-MYSQL-EAR": "name | value\n-----\nencryption_at_rest_enabled | false",
    },
}


def _mock_connector_result(output: str):
    from modules.operations.engines.query_connectors import ConnectorResult

    rows = sum(1 for ln in output.splitlines() if ln.strip())
    return ConnectorResult(success=True, output=output, duration_ms=1,
                           metadata={"rows_returned": rows, "mode": "demo"})


def build_demo_executor(app_id: str, *, persist: bool = False, scheduled: bool = False) -> Callable[[str, str], dict[str, Any]]:
    """Build an :data:`Executor` that returns fixed mock evidence for ``app_id``.

    Any ``predefined_query_id`` not covered by this app's mock map falls back
    to :func:`~modules.operations.engines.predefined_queries_engine.run_predefined_query`
    only for CloudKMS controls (also permanently mock — never a live call);
    anything else reports "no demo evidence configured" rather than silently
    reaching a live connector.
    """
    from modules.operations.engines.connector_common import complete_connector_execution
    from modules.operations.engines.predefined_queries_engine import (
        get_control_by_id,
        set_execution_persist,
    )

    mapping = _DEMO_MOCK_OUTPUTS.get(app_id, {})

    def _run(control_id: str, user: str) -> dict[str, Any]:
        control = get_control_by_id(control_id)
        if control is None:
            return {"ok": False, "error": "Control not found", "error_type": "missing_control"}

        output = mapping.get(control_id)
        if output is None:
            if control.get("technology") == "CloudKMS":
                from modules.operations.engines.predefined_queries_engine import run_cloud_kms_query

                return run_cloud_kms_query(control_id, user)
            return {
                "ok": False,
                "error": f"No demo mock evidence configured for {control_id} in {app_id}",
                "error_type": "missing_query",
            }

        set_execution_persist(persist or scheduled)
        try:
            result = _mock_connector_result(output)
            return complete_connector_execution(
                control, user, control.get("technology") or "", control.get("query") or "", result
            )
        finally:
            set_execution_persist(False)

    return _run


#: Mock connector *output text* keyed by canonical technology label (not by
#: hardcoded app id) — used for the generic Application Onboarding intake
#: path (:func:`~modules.operations.engines.common_control_onboarding.
#: onboard_from_intake_payload`), which onboards whatever technology the user
#: actually typed into the Database Technology / Middleware Technology / OS
#: Linux Technology fields, not one of the three fixed :data:`DEMO_PORTFOLIO`
#: apps. Covers the predefined queries all six evaluable reusable controls
#: need (CC-AUDIT_LOGGING, CC-ENCRYPTION_IN_TRANSIT,
#: CC-IDENTITY_PRIVILEGED_ACCESS, CC-PASSWORD_POLICY,
#: CC-SECURE_CONFIGURATION, CC-VULNERABILITY_PATCH) for whichever technology
#: an intake asset actually resolves to — CC-ENCRYPTION_AT_REST already
#: resolves via the permanently-mock CloudKMS query regardless of this table.
_INTAKE_TECH_MOCK_OUTPUTS: dict[str, dict[str, str]] = {
    "PostgreSQL": {
        "PGX-001": "ssl\n---\non",
        "PGX-002": "name | setting\n------\npassword_encryption | scram-sha-256",
        "PGX-004": "rolname\n-------\napp_admin",
        "PGX-008": "extname\n-------\npgaudit",
        "PGX-013": "name | setting\n------\nlog_connections | on\nlog_statement | mod",
    },
    "YugabyteDB": {
        "YBX-008": "name | setting\n------\nssl | on\npassword_encryption | scram-sha-256",
        "YBX-004": "rolname\n-------\nyb_admin",
        "YBX-011": "name | setting\n------\nlog_connections | on",
    },
    "Aurora MySQL": {
        "MYX-001": "Variable_name | Value\n----------------------\nhave_ssl | YES",
        "MYX-002": "Variable_name | Value\n----------------------\nrequire_secure_transport | ON",
        "MYX-003": "Variable_name | Value\n----------------------\nlog_bin | ON",
        "MYX-004": "Variable_name | Value\n----------------------\nserver_audit_logging | ON",
        "MYX-005": "user | host | plugin\n------------------------\napp_admin | % | caching_sha2_password",
        "MYX-009": "Grants\n-----------------------\nGRANT SELECT ON *.* TO 'app_admin'@'%'",
    },
    # MySQL (GCP Cloud SQL) only has EIT + password-policy rules in the pack
    # (audit-logging / identity-privileged-access are Aurora-MySQL-only — see
    # config/common_control_rules.yaml) — those two controls stay
    # NOT_APPLICABLE for this technology by rule-pack design, not a gap here.
    "MySQL": {
        "MYX-001": "Variable_name | Value\n----------------------\nhave_ssl | YES",
        "MYX-002": "Variable_name | Value\n----------------------\nrequire_secure_transport | ON",
        "MYX-005": "user | host | plugin\n------------------------\napp_admin | % | caching_sha2_password",
    },
    "NGINX": {
        "NGX-003": "ssl_protocols TLSv1.2 TLSv1.3;",
        "NGX-004": "ssl_ciphers HIGH:!MEDIUM;",
        "NGX-006": "access_log /var/log/nginx/access.log main;",
    },
    # OS / Linux Technology intake field. All three also carry a rule for
    # CC-SECURE_CONFIGURATION; Linux additionally has CC-IDENTITY_PRIVILEGED_
    # ACCESS rules (LNX-007/008) and RHEL 8.x/9.x additionally have a
    # CC-AUDIT_LOGGING rule (RH{8,9}-005 auditd) — every predefined query any
    # rule in config/common_control_rules.yaml references for these
    # technologies needs an entry here, or that one rule (and therefore the
    # whole control, once aggregated with the DB/middleware asset) comes back
    # PARTIAL/UNKNOWN instead of a clean verdict. CC-VULNERABILITY_PATCH only
    # has a rule for Linux and RHEL 8.x (no RHEL 9.x rule in the pack — stays
    # NOT_APPLICABLE there, not a gap here).
    "Linux": {
        "LNX-005": "PermitRootLogin no",
        "LNX-006": "PasswordAuthentication no",
        "LNX-007": "%wheel ALL=(ALL) ALL",
        "LNX-008": "root:x:0:0:root:/root:/bin/bash\napp:x:1000:1000::/home/app:/bin/bash",
        "OS-001": "",
    },
    "Red Hat Enterprise Linux 8.x": {
        "RH8-005": "active (running)",
        "RH8-006": "PermitRootLogin no",
        "RH8-007": "PasswordAuthentication no",
        "RH8-004": "active (running)",
        "RH8-008": "kernel-4.18.0-500.el8_8.x86_64 - security update - 2026-01-15",
    },
    "Red Hat Enterprise Linux 9.x": {
        "RH9-005": "active (running)",
        "RH9-006": "PermitRootLogin no",
        "RH9-007": "PasswordAuthentication no",
        "RH9-004": "active (running)",
    },
}


def build_intake_demo_executor() -> Callable[[str, str], dict[str, Any]]:
    """Demo-mode executor for the generic Application Onboarding intake path.

    Mirrors :func:`build_demo_executor` but keys mock evidence off the
    *technology* a control targets (resolved the same way the real rule
    engine resolves it) instead of a hardcoded app id — so verdicts stay
    traceable to whatever the user actually typed into the intake form's
    Database Technology / Middleware Technology fields, not a blanket
    hardcoded pass. A technology/control combination this table doesn't
    cover reports "no demo evidence configured" (matching
    :func:`build_demo_executor`'s own fallback) rather than reaching a live
    connector — this path never opens a real socket.
    """
    from modules.operations.engines.connector_common import complete_connector_execution
    from modules.operations.engines.predefined_queries_engine import get_control_by_id, set_execution_persist

    def _run(control_id: str, user: str) -> dict[str, Any]:
        try:
            control = get_control_by_id(control_id)
            if control is None:
                return {"ok": False, "error": "Control not found", "error_type": "missing_control"}

            technology = control.get("technology") or ""
            if technology == "CloudKMS":
                from modules.operations.engines.predefined_queries_engine import run_cloud_kms_query

                return run_cloud_kms_query(control_id, user)

            output = _INTAKE_TECH_MOCK_OUTPUTS.get(technology, {}).get(control_id)
            if output is None:
                return {
                    "ok": False,
                    "error": f"No demo mock evidence configured for {control_id} ({technology or 'unknown technology'})",
                    "error_type": "missing_query",
                }

            # Preview-only evaluation (this executor only ever runs when the
            # intake path has no explicit executor and isn't persisting — see
            # onboard_from_intake_payload) — pin persist=False explicitly
            # rather than inheriting whatever the process-global execution
            # flag happens to be, matching build_demo_executor's own
            # set_execution_persist(...) / finally-reset discipline.
            set_execution_persist(False)
            try:
                result = _mock_connector_result(output)
                return complete_connector_execution(control, user, technology, control.get("query") or "", result)
            finally:
                set_execution_persist(False)
        except Exception as exc:  # noqa: BLE001 - one control's mock evidence must
            # never abort the whole evaluation (evaluate_controls_for_assets has
            # no per-control isolation of its own); degrade to a normal UNKNOWN
            # rule outcome for this control instead of raising past the caller.
            return {"ok": False, "error": f"Demo evidence unavailable: {exc}", "error_type": "missing_query"}

    return _run


def onboard_demo_application(app_id: str, *, user: str = "demo", persist: bool = False) -> dict[str, Any]:
    """Onboard one EAR/EIT demo fixture app through the standard pipeline.

    Identical to :func:`~modules.operations.engines.common_control_onboarding.
    onboard_application` except the executor is the deterministic mock built
    above — no live connector is ever contacted.
    """
    from modules.operations.engines.common_control_onboarding import onboard_application

    executor = build_demo_executor(app_id, persist=persist, scheduled=persist)
    return onboard_application(
        app_id, executor=executor, persist=persist, user=user, portfolio=DEMO_PORTFOLIO
    )
