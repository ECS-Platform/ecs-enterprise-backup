"""FastAPI routes for evidence upload, repository, and audit package APIs."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse

from modules.shared.services.evidence_api import (
    export_audit_package,
    generate_audit_package,
    get_evidence_by_id,
    list_evidence_repository,
    revalidate_evidence,
    submit_evidence,
    upload_evidence,
)


def register_evidence_routes(app, templates):
    @app.get("/mvp/bulk-upload")
    def mvp_bulk_upload_alias(
        role: str = "owner",
        user: str = "User",
        framework: str = "",
        application: str = "",
        control: str = "",
    ):
        """Legacy alias — prevents 404 from Upload Evidence links."""
        q = f"role={quote(role)}&user={quote(user)}"
        if framework:
            q += f"&framework={quote(framework)}"
        if application:
            q += f"&application={quote(application)}"
        if control:
            q += f"&control={quote(control)}"
        return RedirectResponse(url=f"/mvp/upload?{q}", status_code=307)

    @app.post("/evidence/upload")
    async def evidence_upload_api(
        request: Request,
        role: str = Form("owner"),
        user: str = Form("User"),
        framework: str = Form("PCI DSS"),
        application: str = Form("Net Banking"),
        control: str = Form(""),
        owner: str = Form(""),
        comments: str = Form(""),
        evidence_type: str = Form("Document"),
        audit_cycle: str = Form("Q2 2026"),
        return_url: str = Form(""),
        evidence_file: UploadFile | None = File(None),
    ):
        from modules.shared.services.role_permissions import can_upload_evidence

        if not can_upload_evidence(role):
            err = {
                "status": "error",
                "message": "Access denied: Auditors and executives cannot upload or replace evidence.",
            }
            if request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", ""):
                return JSONResponse(err, status_code=403)
            return RedirectResponse(
                url=f"/dashboard?role={role}&user={quote(user)}&notice={quote(err['message'])}",
                status_code=303,
            )
        try:
            content = b""
            filename = "evidence_upload.pdf"
            if evidence_file and evidence_file.filename:
                content = await evidence_file.read()
                filename = evidence_file.filename
            result = upload_evidence(
                filename=filename,
                content=content,
                framework=framework,
                application=application,
                control=control,
                uploaded_by=user,
                comments=comments,
                evidence_type=evidence_type,
                audit_cycle=audit_cycle,
                owner=owner or user,
            )
            accept = request.headers.get("accept", "")
            wants_json = "application/json" in accept or request.headers.get("x-requested-with") == "XMLHttpRequest"
            if wants_json or not return_url:
                return JSONResponse(result)
            notice = quote(result["message"])
            dest = return_url or f"/framework/{quote(framework)}?role={role}&user={quote(user)}&fw_tab=evidence&notice={notice}"
            sep = "&" if "?" in dest else "?"
            if "notice=" not in dest:
                dest = f"{dest}{sep}notice={notice}"
            return RedirectResponse(url=dest, status_code=303)
        except Exception as exc:
            err = {"status": "error", "message": "Evidence upload service temporarily unavailable.", "detail": str(exc)}
            return JSONResponse(err, status_code=503)

    @app.post("/evidence/revalidate")
    async def evidence_revalidate_api(
        request: Request,
        role: str = Form("owner"),
        user: str = Form("User"),
        framework: str = Form(...),
        control: str = Form(""),
        application: str = Form("Net Banking"),
        return_url: str = Form(""),
    ):
        try:
            result = revalidate_evidence(
                framework=framework,
                control=control,
                application=application,
                user=user,
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JSONResponse(result)
            notice = quote(result["message"])
            dest = return_url or f"/framework/{quote(framework)}?role={role}&user={quote(user)}&fw_tab=controls&notice={notice}"
            return RedirectResponse(url=dest, status_code=303)
        except Exception:
            return JSONResponse(
                {"status": "error", "message": "Evidence upload service temporarily unavailable."},
                status_code=503,
            )

    @app.post("/evidence/submit")
    async def evidence_submit_api(
        request: Request,
        role: str = Form("owner"),
        user: str = Form("User"),
        framework: str = Form(...),
        control: str = Form(""),
        application: str = Form("Net Banking"),
        evidence_id: str = Form(""),
        return_url: str = Form(""),
    ):
        from modules.shared.services.role_permissions import can_submit_to_auditor

        if not can_submit_to_auditor(role):
            err = {"status": "error", "message": "Access denied: only App Owners may submit evidence to auditor review."}
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JSONResponse(err, status_code=403)
            return RedirectResponse(
                url=f"/dashboard?role={role}&user={quote(user)}&notice={quote(err['message'])}",
                status_code=303,
            )
        try:
            result = submit_evidence(
                framework=framework,
                control=control,
                application=application,
                evidence_id=evidence_id,
                user=user,
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JSONResponse(result)
            notice = quote(result["message"])
            dest = return_url or f"/framework/{quote(framework)}?role={role}&user={quote(user)}&fw_tab=evidence&notice={notice}"
            return RedirectResponse(url=dest, status_code=303)
        except Exception:
            return JSONResponse(
                {"status": "error", "message": "Evidence upload service temporarily unavailable."},
                status_code=503,
            )

    @app.get("/evidence/repository")
    def evidence_repository_api(limit: int = 100):
        return JSONResponse(list_evidence_repository(limit=limit))

    @app.get("/evidence/{evidence_id}")
    def evidence_detail_api(evidence_id: str):
        result = get_evidence_by_id(evidence_id)
        if result.get("status") == "error":
            return JSONResponse(result, status_code=404)
        return JSONResponse(result)

    @app.post("/audit/package/generate")
    async def audit_package_generate_api(
        request: Request,
        role: str = Form("cio"),
        user: str = Form("User"),
        return_url: str = Form(""),
    ):
        try:
            result = generate_audit_package(user=user, role=role)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JSONResponse(result)
            notice = quote(f"Audit package {result['package_name']} generated.")
            dest = return_url or f"/mvp/audit-prep?role={role}&user={quote(user)}&show_modal=package&notice={notice}"
            return RedirectResponse(url=dest, status_code=303)
        except Exception:
            return JSONResponse(
                {"status": "error", "message": "Audit package generation temporarily unavailable."},
                status_code=503,
            )

    @app.get("/audit/package/export")
    def audit_package_export_api(
        package_id: str = "",
        role: str = "cio",
        user: str = "User",
        format: str = "json",
    ):
        try:
            result = export_audit_package(package_id=package_id)
            if format == "json":
                return JSONResponse(result)
            lines = [
                f"ECS Evidence Export Bundle — {result.get('bundle_name', 'export')}",
                f"Scope: {result.get('scope', '—')}",
                f"Frameworks: {result.get('frameworks_included', '—')}",
                f"Evidence count: {result.get('evidence_count', 0)}",
                f"Generated: {result.get('exported_at', '—')}",
            ]
            return PlainTextResponse("\n".join(lines), media_type="text/plain")
        except Exception:
            return JSONResponse(
                {"status": "error", "message": "Export service temporarily unavailable."},
                status_code=503,
            )
