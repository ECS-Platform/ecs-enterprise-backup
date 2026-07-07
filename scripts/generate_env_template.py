#!/usr/bin/env python3
"""Generate safe ``.env.uat.template`` / ``.env.prod.template`` files for ECS.

Emits environment templates for the ECS enterprise integrations, grouped by
technology/integration, with an explanatory comment on every variable and
**placeholder values only** — never real IPs, hostnames, or secrets.

USAGE
-----
    python scripts/generate_env_template.py                 # writes both templates
    python scripts/generate_env_template.py --env uat       # only .env.uat.template
    python scripts/generate_env_template.py --env prod      # only .env.prod.template
    python scripts/generate_env_template.py --stdout        # print, write nothing
    python scripts/generate_env_template.py --force         # overwrite existing files

SAFETY
------
* Every value is a ``<placeholder>`` (or a safe non-secret default like a port /
  timeout). No secret is ever emitted.
* By default the generator refuses to overwrite an existing ``.env.uat`` /
  ``.env.prod`` (the real, git-ignored files). It writes to the ``*.template``
  names, which are safe to commit. ``--force`` is required to overwrite an
  existing *target* path.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Var:
    """One environment variable in a template."""
    name: str
    comment: str
    placeholder: str = ""      # value written for the UAT/prod template
    secret: bool = False       # secrets always render as <do-not-commit-*>
    default: str = ""          # non-secret safe default (ports, timeouts)

    def render_value(self) -> str:
        if self.secret:
            return "<do-not-commit>"
        if self.default:
            return self.default
        return self.placeholder or "<set-me>"


@dataclass(frozen=True)
class Group:
    title: str
    note: str
    variables: tuple[Var, ...]


# --------------------------------------------------------------------------- #
# Template model — grouped by technology / integration. Placeholders only.
# --------------------------------------------------------------------------- #
def _timeout(prefix: str) -> Var:
    return Var(f"{prefix}_TIMEOUT_SECONDS", "Request timeout (seconds).", default="30")


GROUPS: tuple[Group, ...] = (
    Group("Core runtime", "ECS process/runtime settings (non-secret).", (
        Var("ECS_ENV", "Active environment name (uat | prod). Drives config resolution.",
            placeholder="uat"),
        Var("ECS_AUTH_ENABLED", "Enable auth/RBAC (true in real environments).",
            default="true"),
        Var("ECS_VALIDATE_CONFIG", "Config validation mode (on | warn | off).",
            default="on"),
    )),
    Group("Audit persistence (Postgres)",
          "Durable audit-intelligence store. Provision Postgres and apply "
          "docs/DB_SCHEMA_AUDIT_INTELLIGENCE.sql. Source the URL from a secret manager.", (
        Var("ECS_AUDIT_DB_URL",
            "SQLAlchemy/psycopg URL, e.g. postgresql://<user>:<pw>@<host>:5432/<db>. "
            "Contains a credential -> treat as a secret.", secret=True),
    )),
    Group("Oracle", "Read-only service account for Oracle baselining checks.", (
        Var("ECS_ORACLE_HOST", "Oracle host or FQDN (no real value in Git).",
            placeholder="<uat-oracle-host>"),
        Var("ECS_ORACLE_PORT", "Oracle listener port.", default="1521"),
        Var("ECS_ORACLE_SERVICE_NAME", "Oracle service name.", placeholder="<service-name>"),
        Var("ECS_ORACLE_USER", "Read-only service account.", placeholder="<service-account>"),
        Var("ECS_ORACLE_PASSWORD", "Oracle password.", secret=True),
        _timeout("ECS_ORACLE"),
    )),
    Group("PostgreSQL", "Read-only service account for PostgreSQL checks.", (
        Var("ECS_PG_HOST", "PostgreSQL host or FQDN.", placeholder="<uat-postgres-host>"),
        Var("ECS_PG_PORT", "PostgreSQL port.", default="5432"),
        Var("ECS_PG_DATABASE", "Database name.", placeholder="<database>"),
        Var("ECS_PG_USER", "Read-only service account.", placeholder="<service-account>"),
        Var("ECS_PG_PASSWORD", "PostgreSQL password.", secret=True),
        Var("ECS_PG_SSLMODE", "TLS mode (require in real envs).", default="require"),
        _timeout("ECS_PG"),
    )),
    Group("YugabyteDB", "Read-only service account for YugabyteDB (PG wire).", (
        Var("ECS_YB_HOST", "Yugabyte host or FQDN.", placeholder="<uat-yugabyte-host>"),
        Var("ECS_YB_PORT", "Yugabyte YSQL port.", default="5433"),
        Var("ECS_YB_DATABASE", "Database name.", placeholder="<database>"),
        Var("ECS_YB_USER", "Read-only service account.", placeholder="<service-account>"),
        Var("ECS_YB_PASSWORD", "Yugabyte password.", secret=True),
        Var("ECS_YB_SSLMODE", "TLS mode.", default="require"),
        _timeout("ECS_YB"),
    )),
    Group("MySQL / Aurora", "Read-only account for MySQL / Aurora-MySQL (wire-compatible).", (
        Var("ECS_MYSQL_HOST", "MySQL/Aurora host or FQDN.", placeholder="<uat-mysql-host>"),
        Var("ECS_MYSQL_PORT", "MySQL port.", default="3306"),
        Var("ECS_MYSQL_DATABASE", "Database name.", placeholder="<database>"),
        Var("ECS_MYSQL_USER", "Read-only service account.", placeholder="<service-account>"),
        Var("ECS_MYSQL_PASSWORD", "MySQL password.", secret=True),
        Var("ECS_MYSQL_SSL", "Require TLS (true in real envs).", default="true"),
        _timeout("ECS_MYSQL"),
    )),
    Group("SQL Server", "Read-only service account for SQL Server checks.", (
        Var("ECS_SQLSERVER_HOST", "SQL Server host or FQDN.", placeholder="<uat-sqlserver-host>"),
        Var("ECS_SQLSERVER_PORT", "SQL Server port.", default="1433"),
        Var("ECS_SQLSERVER_DATABASE", "Database name.", placeholder="<database>"),
        Var("ECS_SQLSERVER_USERNAME", "Read-only service account.", placeholder="<service-account>"),
        Var("ECS_SQLSERVER_PASSWORD", "SQL Server password.", secret=True),
        _timeout("ECS_SQLSERVER"),
    )),
    Group("MongoDB", "Connection URI may embed credentials -> treat as secret.", (
        Var("ECS_MONGODB_URI",
            "Mongo URI, e.g. mongodb://<user>:<pw>@<host>:27017/?authSource=admin.",
            secret=True),
        Var("ECS_MONGODB_DATABASE", "Database name.", default="admin"),
        _timeout("ECS_MONGODB"),
    )),
    Group("Redis", "Redis endpoint (password optional depending on deployment).", (
        Var("ECS_REDIS_HOST", "Redis host or FQDN.", placeholder="<uat-redis-host>"),
        Var("ECS_REDIS_PORT", "Redis port.", default="6379"),
        Var("ECS_REDIS_PASSWORD", "Redis password (blank if none).", secret=True),
        _timeout("ECS_REDIS"),
    )),
    Group("Linux / RHEL / NGINX / Apache / Tomcat",
          "OS + middleware targets (roadmap SSH mode; use read-only accounts).", (
        Var("ECS_LINUX_HOST", "Linux/RHEL host or FQDN.", placeholder="<uat-linux-host>"),
        Var("ECS_LINUX_USERNAME", "SSH service account.", placeholder="<ssh-service-account>"),
        Var("ECS_LINUX_AUTH_MODE", "Auth mode (key | password).", default="key"),
        Var("ECS_SSH_KEY_PATH", "Path to the SSH private key (never commit the key).",
            placeholder="<path-to-private-key>"),
        Var("ECS_NGINX_HOST", "NGINX host or FQDN.", placeholder="<uat-nginx-host>"),
        Var("ECS_APACHE_HOST", "Apache host or FQDN.", placeholder="<uat-apache-host>"),
        Var("ECS_TOMCAT_HOST", "Tomcat host or FQDN.", placeholder="<uat-tomcat-host>"),
    )),
    Group("Kubernetes", "Read-only cluster access via kubeconfig.", (
        Var("ECS_KUBECTL_PATH", "kubectl binary path.", default="kubectl"),
        Var("ECS_KUBECONFIG", "Path to the UAT/prod kubeconfig (never commit it).",
            placeholder="<path-to-kubeconfig>"),
        _timeout("ECS_K8S"),
    )),
    Group("OpenShift", "Read-only cluster access via kubeconfig / oc.", (
        Var("ECS_OC_PATH", "oc binary path.", default="oc"),
        Var("ECS_OPENSHIFT_KUBECONFIG", "Path to the OpenShift kubeconfig (never commit it).",
            placeholder="<path-to-kubeconfig>"),
        _timeout("ECS_OPENSHIFT"),
    )),
    Group("ServiceNow CMDB", "OAuth client-credentials for CMDB asset discovery.", (
        Var("ECS_SERVICENOW_BASE_URL", "Instance URL, e.g. https://<instance>.service-now.com.",
            placeholder="https://<instance>.service-now.com"),
        Var("ECS_SERVICENOW_CLIENT_ID", "OAuth client id.", secret=True),
        Var("ECS_SERVICENOW_CLIENT_SECRET", "OAuth client secret.", secret=True),
        _timeout("ECS_SERVICENOW"),
    )),
    Group("Archer", "API token for Archer GRC.", (
        Var("ECS_ARCHER_BASE_URL", "Archer base URL.", placeholder="https://<uat-archer-host>"),
        Var("ECS_ARCHER_API_TOKEN", "Archer API token.", secret=True),
        _timeout("ECS_ARCHER"),
    )),
    Group("SharePoint / Microsoft Graph", "OAuth client-credentials for evidence documents.", (
        Var("ECS_GRAPH_TENANT_ID", "Azure AD tenant id.", secret=True),
        Var("ECS_GRAPH_CLIENT_ID", "App registration client id.", secret=True),
        Var("ECS_GRAPH_CLIENT_SECRET", "App registration client secret.", secret=True),
        Var("ECS_GRAPH_SITE_ID", "Target SharePoint site id.", placeholder="<site-id>"),
        Var("ECS_GRAPH_DRIVE_ID", "Optional drive id.", placeholder="<drive-id-optional>"),
        _timeout("ECS_GRAPH"),
    )),
    Group("Jira", "Basic auth (email + API token).", (
        Var("ECS_JIRA_BASE_URL", "Jira base URL.", placeholder="https://<org>.atlassian.net"),
        Var("ECS_JIRA_USERNAME", "Jira account email.", placeholder="<service-account-email>"),
        Var("ECS_JIRA_API_TOKEN", "Jira API token.", secret=True),
        _timeout("ECS_JIRA"),
    )),
    Group("Confluence", "Basic auth (email + API token).", (
        Var("ECS_CONFLUENCE_BASE_URL", "Confluence base URL.",
            placeholder="https://<org>.atlassian.net/wiki"),
        Var("ECS_CONFLUENCE_USERNAME", "Confluence account email.",
            placeholder="<service-account-email>"),
        Var("ECS_CONFLUENCE_API_TOKEN", "Confluence API token.", secret=True),
        _timeout("ECS_CONFLUENCE"),
    )),
    Group("SonarQube", "Token auth (AppSec quality-gate / issue evidence).", (
        Var("ECS_SONARQUBE_BASE_URL", "SonarQube base URL.", placeholder="https://<uat-sonarqube-host>"),
        Var("ECS_SONARQUBE_TOKEN", "SonarQube user token.", secret=True),
        _timeout("ECS_SONARQUBE"),
    )),
    Group("Checkmarx", "OAuth client-credentials (SAST scan evidence).", (
        Var("ECS_CHECKMARX_BASE_URL", "Checkmarx base URL.", placeholder="https://<uat-checkmarx-host>"),
        Var("ECS_CHECKMARX_CLIENT_ID", "Checkmarx client id.", secret=True),
        Var("ECS_CHECKMARX_CLIENT_SECRET", "Checkmarx client secret.", secret=True),
        _timeout("ECS_CHECKMARX"),
    )),
    Group("Prisma Cloud", "Access-key / secret-key (cloud posture / compliance).", (
        Var("ECS_PRISMA_CLOUD_BASE_URL", "Prisma Cloud API URL.",
            placeholder="https://<api-region>.prismacloud.io"),
        Var("ECS_PRISMA_CLOUD_ACCESS_KEY", "Prisma Cloud access key.", secret=True),
        Var("ECS_PRISMA_CLOUD_SECRET_KEY", "Prisma Cloud secret key.", secret=True),
        _timeout("ECS_PRISMA_CLOUD"),
    )),
    Group("Tripwire", "Basic auth (username + password) for file-integrity evidence.", (
        Var("ECS_TRIPWIRE_BASE_URL", "Tripwire base URL.", placeholder="https://<uat-tripwire-host>"),
        Var("ECS_TRIPWIRE_USERNAME", "Tripwire service account.", placeholder="<service-account>"),
        Var("ECS_TRIPWIRE_PASSWORD", "Tripwire password.", secret=True),
        _timeout("ECS_TRIPWIRE"),
    )),
)


def render_template(env_name: str) -> str:
    """Render the full template text for ``uat`` or ``prod``."""
    label = env_name.lower()
    lines = [
        f"# ECS environment template — .env.{label}",
        "# =============================================================================",
        "# PLACEHOLDERS ONLY. Copy to `.env.%s`, replace every <...>, and NEVER commit" % label,
        "# the populated file (.gitignore already blocks .env.* except .env.example).",
        "# Source secrets from a managed secret store in production; do not paste real",
        "# IPs, hostnames, tokens, or passwords into any committed file.",
        "# =============================================================================",
        "",
        f"ECS_ENV={label}",
        "",
    ]
    for group in GROUPS:
        lines.append(f"# --- {group.title} " + "-" * max(3, 60 - len(group.title)))
        if group.note:
            lines.append(f"# {group.note}")
        for var in group.variables:
            if var.name == "ECS_ENV":
                continue  # already emitted at the top
            lines.append(f"# {var.comment}")
            lines.append(f"{var.name}={var.render_value()}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def all_variable_names() -> list[str]:
    names: list[str] = ["ECS_ENV"]
    for group in GROUPS:
        for var in group.variables:
            if var.name not in names:
                names.append(var.name)
    return names


def _target_and_template_paths(env_name: str, out_dir: Path) -> tuple[Path, Path]:
    real = out_dir / f".env.{env_name}"
    template = out_dir / f".env.{env_name}.template"
    return real, template


def write_template(env_name: str, out_dir: Path, *, force: bool) -> tuple[Path, str]:
    """Write one template file. Returns (path, action). Refuses to clobber .env.<env>."""
    real, template = _target_and_template_paths(env_name, out_dir)
    # Guard: never overwrite the real env file; only ever write the *.template.
    if real.exists() and not force:
        # Still allowed to (re)write the template; the guard is about the REAL file.
        pass
    if template.exists() and not force:
        return template, "skipped-exists"
    content = render_template(env_name)
    template.write_text(content, encoding="utf-8")
    return template, "written"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate safe .env.uat.template / .env.prod.template files.")
    parser.add_argument("--env", choices=["uat", "prod", "both"], default="both",
                        help="Which template(s) to generate (default: both).")
    parser.add_argument("--out-dir", default=str(ROOT),
                        help="Directory to write templates into (default: repo root).")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing template files.")
    parser.add_argument("--stdout", action="store_true",
                        help="Print template(s) to stdout; write nothing.")
    args = parser.parse_args(argv)

    envs = ["uat", "prod"] if args.env == "both" else [args.env]
    out_dir = Path(args.out_dir).resolve()

    if args.stdout:
        for env_name in envs:
            print(render_template(env_name))
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for env_name in envs:
        path, action = write_template(env_name, out_dir, force=args.force)
        rel = path.relative_to(out_dir) if path.is_relative_to(out_dir) else path
        if action == "skipped-exists":
            print(f"skip  {rel} (exists; use --force to overwrite)")
        else:
            print(f"write {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
