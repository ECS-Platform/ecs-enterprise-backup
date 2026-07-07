# ECS Demo Mode Setup & Troubleshooting Guide

## Purpose

This document explains how to run ECS locally in Demo Mode without Azure AD authentication, JWT tokens, or RBAC enforcement.

This guide was created after resolving the "Missing Authorization Header" issue encountered during local setup.

---

# Symptoms

When accessing ECS pages:

```json
{
  "error": "unauthorized",
  "reason": "missing_token",
  "detail": "Missing or malformed Authorization header."
}
```

or

HTTP 401 Unauthorized

especially on:

* /dashboard
* /mvp/roi
* /mvp/trends
* Executive Overview pages

---

# Root Cause

The ECS authentication bypass code was already present and working.

The actual problem was:

The running Uvicorn process did not receive the required environment variables.

Specifically:

```bash
DEMO_MODE=true
ECS_AUTH_ENABLED=false
RBAC_ENFORCEMENT_ENABLED=false
RBAC_PAGE_ENFORCEMENT_ENABLED=false
```

were visible in the terminal but were not available inside the ECS server process.

As a result:

```python
os.environ.get("DEMO_MODE")
```

returned:

```python
None
```

and ECS continued enforcing authentication.

---

# Required Branch

Switch to:

```bash
git checkout cursor/predefined-queries-module
git pull origin cursor/predefined-queries-module
```

Verify:

```bash
git log --oneline -5
```

Recent commits should include:

* Add ECS ROI workbook
* roi-executive-dashboard-v2
* demo-ready-2026-06-14

---

# Required File

Verify:

```bash
find . -name "accessibility_theme.html"
```

Expected:

```text
modules/shared/templates/partials/accessibility_theme.html
```

If missing:

Pull the latest branch again.

---

# Environment Variables

For Git Bash:

```bash
export DEMO_MODE=true
export ECS_AUTH_ENABLED=false
export RBAC_ENFORCEMENT_ENABLED=false
export RBAC_PAGE_ENFORCEMENT_ENABLED=false
```

Verify:

```bash
echo $DEMO_MODE
```

Expected:

```text
true
```

Verify Python can see it:

```bash
python -c "import os; print(os.environ.get('DEMO_MODE'))"
```

Expected:

```text
true
```

---

# Starting ECS

IMPORTANT:

Start ECS from the SAME terminal session where the environment variables were exported.

Run:

```bash
uvicorn app.main:app
```

Do NOT open a new terminal.

Do NOT start ECS from another shell.

Do NOT rely on .env files.

Current ECS build reads:

```python
os.environ
```

directly.

No dotenv loading is configured.

---

# Validation

Test:

```bash
curl -I http://127.0.0.1:8000/dashboard
```

Expected:

```text
HTTP/1.1 200 OK
```

Test:

```bash
curl http://127.0.0.1:8000/dashboard
```

Expected:

HTML page content.

NOT:

```json
{
  "error": "unauthorized",
  "reason": "missing_token"
}
```

---

# Known Non-Blocking Warning

The following warning may appear:

```text
Evidence repository unavailable:
could not translate host name "postgres" to address
```

This means:

* PostgreSQL container not running
* Local database unavailable

This does NOT prevent the ECS demo from running.

---

# Common Mistakes

## Mistake 1

Running:

```powershell
set DEMO_MODE=true
```

in PowerShell.

Use:

```powershell
$env:DEMO_MODE="true"
```

instead.

---

## Mistake 2

Exporting variables and opening a new terminal.

Environment variables are terminal-session specific.

Re-export variables in the terminal that launches ECS.

---

## Mistake 3

Assuming .env is loaded automatically.

Current ECS build does NOT use:

```python
load_dotenv()
```

and does NOT automatically load:

```text
.env
```

Environment variables must be supplied explicitly.

---

# Successful Result

When configured correctly:

* Dashboard loads
* Executive Overview loads
* ROI screens load
* Trends load
* Authentication is bypassed
* Azure AD is bypassed
* JWT validation is bypassed
* No Authorization header is required

---

# Summary

Issue:

Authentication still enforced despite Demo Mode.

Root Cause:

Running ECS process did not receive:

```bash
DEMO_MODE=true
```

Resolution:

Export environment variables in the same shell that launches Uvicorn.

Status:

Resolved.
