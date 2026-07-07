"""Tests for scripts/generate_env_template.py.

Verifies the generator emits placeholder-only, grouped, commented templates with
no real IPs or secret values, writes to ``*.template`` (never clobbering a real
``.env.*``), honours ``--force``, and supports ``--stdout``. All file writes go to
a pytest ``tmp_path`` — the repo is never modified.
"""

from __future__ import annotations

import os
import re

os.environ.setdefault("ECS_VALIDATE_CONFIG", "off")

import pytest

import scripts.generate_env_template as gen

IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")

#: Values that would indicate a real secret leaked into a template.
FORBIDDEN_SECRET_MARKERS = ("password=super", "token=eyj", "secret=aws", "BEGIN RSA")


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("env_name", ["uat", "prod"])
def test_render_has_header_and_env(env_name):
    text = gen.render_template(env_name)
    assert f".env.{env_name}" in text
    assert f"ECS_ENV={env_name}" in text
    assert "PLACEHOLDERS ONLY" in text


@pytest.mark.parametrize("env_name", ["uat", "prod"])
def test_render_contains_all_integration_groups(env_name):
    text = gen.render_template(env_name)
    for title in ("Oracle", "PostgreSQL", "YugabyteDB", "MySQL / Aurora", "SQL Server",
                  "MongoDB", "Redis", "Kubernetes", "OpenShift", "ServiceNow CMDB",
                  "Archer", "SharePoint / Microsoft Graph", "Jira", "Confluence",
                  "SonarQube", "Checkmarx", "Prisma Cloud", "Tripwire"):
        assert f"--- {title} " in text, f"missing group: {title}"


@pytest.mark.parametrize("env_name", ["uat", "prod"])
def test_every_variable_has_a_comment(env_name):
    text = gen.render_template(env_name)
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "=" in line and not line.startswith("#") and line.strip():
            # The preceding non-blank line should be a comment.
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            assert lines[j].startswith("#"), f"variable without comment: {line!r}"


@pytest.mark.parametrize("env_name", ["uat", "prod"])
def test_secrets_render_as_placeholder(env_name):
    text = gen.render_template(env_name)
    # Every secret var must be <do-not-commit>, never an inline value.
    for group in gen.GROUPS:
        for var in group.variables:
            if var.secret:
                assert f"{var.name}=<do-not-commit>" in text, f"{var.name} not masked"


@pytest.mark.parametrize("env_name", ["uat", "prod"])
def test_no_real_ip_addresses(env_name):
    text = gen.render_template(env_name)
    for ip in IP_RE.findall(text):
        assert ip.startswith(("127.", "0.0.0.0")), f"real IP in template: {ip}"


@pytest.mark.parametrize("env_name", ["uat", "prod"])
def test_no_obvious_secret_values(env_name):
    text = gen.render_template(env_name).lower()
    for marker in FORBIDDEN_SECRET_MARKERS:
        assert marker.lower() not in text


def test_safe_defaults_present():
    text = gen.render_template("uat")
    assert "ECS_PG_PORT=5432" in text
    assert "ECS_ORACLE_PORT=1521" in text
    assert "ECS_ORACLE_TIMEOUT_SECONDS=30" in text


def test_all_variable_names_unique_and_prefixed():
    names = gen.all_variable_names()
    assert len(names) == len(set(names)), "duplicate variable names"
    assert all(n == "ECS_ENV" or n.startswith("ECS_") for n in names)


# --------------------------------------------------------------------------- #
# File writing (isolated to tmp_path)
# --------------------------------------------------------------------------- #
def test_write_both_templates(tmp_path):
    rc = gen.main(["--env", "both", "--out-dir", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".env.uat.template").exists()
    assert (tmp_path / ".env.prod.template").exists()
    # Real env files must NOT be created.
    assert not (tmp_path / ".env.uat").exists()
    assert not (tmp_path / ".env.prod").exists()


def test_write_single_env(tmp_path):
    gen.main(["--env", "uat", "--out-dir", str(tmp_path)])
    assert (tmp_path / ".env.uat.template").exists()
    assert not (tmp_path / ".env.prod.template").exists()


def test_skip_existing_template_without_force(tmp_path):
    tpl = tmp_path / ".env.uat.template"
    tpl.write_text("PRE-EXISTING", encoding="utf-8")
    gen.main(["--env", "uat", "--out-dir", str(tmp_path)])
    assert tpl.read_text(encoding="utf-8") == "PRE-EXISTING"  # untouched


def test_force_overwrites_template(tmp_path):
    tpl = tmp_path / ".env.uat.template"
    tpl.write_text("PRE-EXISTING", encoding="utf-8")
    gen.main(["--env", "uat", "--out-dir", str(tmp_path), "--force"])
    assert "ECS_ENV=uat" in tpl.read_text(encoding="utf-8")


def test_does_not_overwrite_real_env_file(tmp_path):
    # A populated real .env.uat must never be clobbered by the generator.
    real = tmp_path / ".env.uat"
    real.write_text("ECS_JIRA_API_TOKEN=REALSECRET\n", encoding="utf-8")
    gen.main(["--env", "uat", "--out-dir", str(tmp_path)])
    assert real.read_text(encoding="utf-8") == "ECS_JIRA_API_TOKEN=REALSECRET\n"
    # The template is a separate file.
    assert (tmp_path / ".env.uat.template").exists()
    assert "REALSECRET" not in (tmp_path / ".env.uat.template").read_text(encoding="utf-8")


def test_stdout_mode_writes_nothing(tmp_path, capsys):
    rc = gen.main(["--env", "both", "--out-dir", str(tmp_path), "--stdout"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ECS_ENV=uat" in out and "ECS_ENV=prod" in out
    assert not (tmp_path / ".env.uat.template").exists()  # nothing written


def test_written_template_is_parseable_keyvals(tmp_path):
    gen.main(["--env", "prod", "--out-dir", str(tmp_path)])
    text = (tmp_path / ".env.prod.template").read_text(encoding="utf-8")
    kv = [l for l in text.splitlines() if l and not l.startswith("#")]
    for line in kv:
        assert "=" in line, f"non key=value line: {line!r}"
        key = line.split("=", 1)[0]
        assert key == key.strip() and " " not in key
