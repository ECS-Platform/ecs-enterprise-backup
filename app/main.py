
from contextlib import asynccontextmanager
from urllib.parse import quote

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import ecs_state
from app.chatbot_enhanced import (
    FALLBACK,
    format_chatbot_response,
    try_enhanced_answer,
    try_framework_definition,
)
from app.demo_seed import seed_demo_workflow_state
from app.evidence_repository import refresh_repository_from_frameworks
from app.framework_catalog import (
    catalog_stats,
    get_framework_controls,
)
from app.framework_dashboards import build_framework_dashboard
from app.enterprise_context import enterprise_widgets_context
from app.audit_trail import log_event, record_approval, record_rejection
from app.evidence_review import build_evidence_review, review_url
from app.routes_mvp import register_mvp_routes
from app.workflow_module import (
    build_auditor_review_queue,
    build_owner_work_queue,
    work_queue_summary,
)

def _workflow_redirect(
    role: str,
    user: str,
    framework_name: str = "",
    return_to: str = "framework",
    notice: str = "",
):
    if return_to == "dashboard":
        url = f"/dashboard?role={role}&user={user}"
    elif return_to == "review":
        url = f"/framework/{framework_name}?role={role}&user={user}"
    else:
        url = f"/framework/{framework_name}?role={role}&user={user}"
    if notice:
        url += f"&notice={quote(notice)}"
    return RedirectResponse(url=url, status_code=303)

@asynccontextmanager
async def ecs_lifespan(application: FastAPI):
    refresh_repository_from_frameworks(source="startup")
    seed_demo_workflow_state()
    yield


app = FastAPI(title="ECS Consolidated Demo V13", lifespan=ecs_lifespan)

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["review_url"] = review_url

# Re-export shared state for backward compatibility with existing code paths
PCI_DSS_MOCK_EVIDENCES = ecs_state.PCI_DSS_MOCK_EVIDENCES
frameworks = ecs_state.frameworks
submitted_controls = ecs_state.submitted_controls
approved_controls = ecs_state.approved_controls
rejected_controls = ecs_state.rejected_controls
scheduler_data = ecs_state.scheduler_data
control_key = ecs_state.control_key
control_status = ecs_state.control_status
build_evidence_analytics = ecs_state.build_evidence_analytics


def chatbot_answer(query: str, role: str = "owner", user: str = "User", framework_hint: str = ""):
    q = query.lower()

    fw_hint = framework_hint
    if not fw_hint:
        for name in ecs_state.frameworks:
            if name.lower() in q:
                fw_hint = name
                break

    enhanced = try_enhanced_answer(query, role=role, user=user)
    if enhanced:
        return enhanced

    definition = try_framework_definition(query)
    if definition:
        from app.chatbot_engine import record_exchange
        record_exchange(user, role, query, definition)
        return definition

    if "reject" in q or "rejection" in q or ("reason" in q and "rejected" in q):
        if not ecs_state.rejected_controls:
            return format_chatbot_response(
                "No rejected evidences in the current workflow state.",
                fw_hint,
            )
        lines = []
        for key, info in list(ecs_state.rejected_controls.items())[:8]:
            _framework, control = key.split("::", 1)
            lines.append(f"{control} ({_framework}): {info['reason']}")
        ans = format_chatbot_response(
            "Rejected evidences and reasons — " + " | ".join(lines),
            fw_hint,
        )
        from app.chatbot_engine import record_exchange
        record_exchange(user, role, query, ans)
        return ans

    from app.chatbot_engine import process_query, record_exchange
    clarification = process_query(query, role=role, user=user)
    if clarification:
        return clarification

    ans = format_chatbot_response(FALLBACK, fw_hint)
    record_exchange(user, role, query, ans)
    return ans


@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


@app.post("/login")
def login(role: str = Form(...)):
    if role == "cio":
        return RedirectResponse(
            url="/dashboard/cio?role=cio&user=CIO",
            status_code=303,
        )
    if role == "vertical_head":
        return RedirectResponse(
            url="/dashboard/vertical-head?role=vertical_head&user=VerticalHead",
            status_code=303,
        )
    if role == "compliance_head" or role == "compliance_officer":
        return RedirectResponse(
            url="/dashboard/compliance-head?role=compliance_head&user=ComplianceOfficer",
            status_code=303,
        )
    if role == "functional_head":
        return RedirectResponse(
            url="/dashboard/functional-head?role=functional_head&user=FunctionalHead",
            status_code=303,
        )

    user = "AppOwner" if role == "owner" else "Auditor"

    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}",
        status_code=303,
    )


@app.get("/logout")
def logout():
    return RedirectResponse("/", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    role: str = "owner",
    user: str = "User",
    response: str = "",
    notice: str = "",
):
    ctx = {
        "frameworks": frameworks.keys(),
        "scheduler_data": scheduler_data,
        "role": role,
        "user": user,
        "response": response,
        "notice": notice,
        "rejected_controls": rejected_controls,
        "owner_work_queue": build_owner_work_queue() if role == "owner" else [],
        "auditor_review_queue": build_auditor_review_queue() if role == "auditor" else [],
        "work_queue_summary": work_queue_summary(),
    }
    ctx.update(enterprise_widgets_context(role, user=user))
    ctx["nav_active"] = "main_dashboard"
    return templates.TemplateResponse(request=request, name="dashboard.html", context=ctx)


@app.get("/dashboard/cio", response_class=HTMLResponse)
def cio_dashboard(
    request: Request,
    role: str = "cio",
    user: str = "CIO",
    response: str = "",
):
    from app.demo_metrics import display_framework_maturity

    analytics = build_evidence_analytics()
    analytics["framework_stats"] = display_framework_maturity(analytics["framework_stats"])
    ctx = {
        "frameworks": frameworks.keys(),
        "scheduler_data": scheduler_data,
        "role": role,
        "user": user,
        "response": response,
        "analytics": analytics,
        "rejected_controls": rejected_controls,
    }
    ctx.update(enterprise_widgets_context(role, user=user))
    return templates.TemplateResponse(request=request, name="cio_dashboard.html", context=ctx)


@app.post("/chat")
def chat(
    query: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    framework_name: str = Form(""),
):
    response = chatbot_answer(query, role=role, user=user, framework_hint=framework_name)
    encoded = quote(response)

    if role == "cio":
        return RedirectResponse(
            url=f"/dashboard/cio?role={role}&user={user}&response={encoded}",
            status_code=303,
        )
    if role == "vertical_head":
        return RedirectResponse(
            url=f"/dashboard/vertical-head?role={role}&user={user}&response={encoded}",
            status_code=303,
        )
    if role == "compliance_head" or role == "compliance_officer":
        return RedirectResponse(
            url=f"/dashboard/compliance-head?role=compliance_head&user={user}&response={encoded}",
            status_code=303,
        )
    if role == "functional_head":
        return RedirectResponse(
            url=f"/dashboard/functional-head?role={role}&user={user}&response={encoded}",
            status_code=303,
        )

    if framework_name:
        return RedirectResponse(
            url=f"/framework/{framework_name}?role={role}&user={user}&response={encoded}",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}&response={encoded}",
        status_code=303,
    )


@app.post("/itpp/action")
def itpp_action(
    action: str = Form(...),
    domain: str = Form(""),
    role: str = Form("owner"),
    user: str = Form("User"),
):
    from app.itpp_module import execute_itpp_action

    notice = execute_itpp_action(action, domain, user, role)
    return RedirectResponse(
        url=f"/framework/ITPP?role={role}&user={user}&notice={quote(notice)}",
        status_code=303,
    )


@app.get("/framework/{framework_name}", response_class=HTMLResponse)
def framework_page(
    request: Request,
    framework_name: str,
    role: str = "owner",
    user: str = "User",
    response: str = "",
    notice: str = "",
):
    catalog_controls = get_framework_controls(framework_name)
    fw_evidence_count = sum(len(c["evidences"]) for c in catalog_controls)

    ctx = {
        "framework_name": framework_name,
        "frameworks": frameworks.keys(),
        "controls": frameworks.get(framework_name, []),
        "framework_catalog_controls": catalog_controls,
        "framework_evidence_count": fw_evidence_count,
        "framework_control_count": len(catalog_controls),
        "catalog_stats": catalog_stats(),
        "fw_dashboard": build_framework_dashboard(framework_name, catalog_controls),
        "role": role,
        "user": user,
        "response": response,
        "notice": notice,
        "submitted_controls": submitted_controls,
        "approved_controls": approved_controls,
        "rejected_controls": rejected_controls,
    }
    ctx.update(enterprise_widgets_context(role, framework=framework_name, user=user))
    return templates.TemplateResponse(
        request=request,
        name="framework.html",
        context=ctx,
    )


@app.get("/evidence/review", response_class=HTMLResponse)
def evidence_review_page(
    request: Request,
    framework_name: str,
    control_name: str,
    evidence_id: str,
    role: str = "owner",
    user: str = "User",
    notice: str = "",
):
    review = build_evidence_review(framework_name, control_name, evidence_id, role, user)
    if not review:
        return RedirectResponse(
            url=f"/framework/{framework_name}?role={role}&user={user}&notice={quote('Evidence not found.')}",
            status_code=303,
        )
    ctx = {
        "framework_name": framework_name,
        "frameworks": frameworks.keys(),
        "role": role,
        "user": user,
        "notice": notice,
        "review": review,
        "submitted_controls": submitted_controls,
        "approved_controls": approved_controls,
        "rejected_controls": rejected_controls,
    }
    ctx.update(enterprise_widgets_context(role, framework=framework_name, user=user))
    return templates.TemplateResponse(request, "evidence_review.html", ctx)


def _review_redirect(framework_name: str, role: str, user: str, notice: str, control_name: str = "", evidence_id: str = ""):
    if control_name and evidence_id:
        url = review_url(framework_name, control_name, evidence_id, role, user)
    else:
        url = f"/framework/{framework_name}?role={role}&user={user}"
    if notice:
        url += f"&notice={quote(notice)}"
    return RedirectResponse(url=url, status_code=303)


@app.post("/evidence/review/submit")
def evidence_review_submit(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    key = control_key(framework_name, control_name)
    if key in approved_controls:
        return _review_redirect(framework_name, role, user, "Cannot resubmit: observation is closed.", control_name, evidence_id)
    was_rejected = key in rejected_controls
    if was_rejected:
        del rejected_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.cancelled_drafts:
        ecs_state.cancelled_drafts.discard(key)
    submitted_controls[key] = "Pending Auditor Review"
    from datetime import datetime, timezone

    ecs_state.submitted_meta[key] = {
        "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "submitted_by": user,
    }
    if key in ecs_state.owner_drafts:
        del ecs_state.owner_drafts[key]
    log_event(
        "Evidence Submitted",
        user,
        framework_name,
        control_name,
        "Submitted to auditor — Pending Auditor Review",
        evidence_id,
        role=role or "App Owner",
    )
    notice = "Evidence resubmitted for auditor review." if was_rejected else "Submitted To Auditor — Pending Auditor Review."
    return _review_redirect(framework_name, role, user, notice, control_name, evidence_id)


@app.post("/evidence/review/approve")
def evidence_review_approve(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    approve(
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        return_to="review",
    )
    return _review_redirect(framework_name, role, user, f"Approved — Observation Closed — Auditor Approved.", control_name, evidence_id)


@app.post("/evidence/review/reject")
def evidence_review_reject(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
):
    reject(
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        reject_reason=reject_reason,
        return_to="review",
    )
    return _review_redirect(framework_name, role, user, f"Rejected By Auditor: {reject_reason.strip()[:80]}", control_name, evidence_id)


@app.post("/evidence/review/clarify")
def evidence_review_clarify(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    message: str = Form(...),
):
    workflow_clarify(
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        message=message,
    )
    return _review_redirect(framework_name, role, user, "Clarification requested from App Owner.", control_name, evidence_id)


@app.post("/evidence/review/reject-internal")
def evidence_review_reject_internal(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
):
    from datetime import datetime, timezone

    reason = reject_reason.strip()
    key = control_key(framework_name, control_name)
    ecs_state.rejected_controls[key] = {
        "reason": reason or "Rejected internally by App Owner — quality review failed.",
        "rejected_by": user,
        "rejected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "internal": True,
    }
    if key in submitted_controls:
        del submitted_controls[key]
    log_event("Rejected Internally", user, framework_name, control_name, reason, evidence_id, role=role)
    return _review_redirect(framework_name, role, user, "Evidence rejected internally.", control_name, evidence_id)


@app.post("/evidence/review/save-draft")
def evidence_review_save_draft(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    owner_note: str = Form(""),
):
    from datetime import datetime, timezone

    key = control_key(framework_name, control_name)
    ecs_state.owner_drafts[key] = {
        "saved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "saved_by": user,
        "note": owner_note.strip(),
    }
    log_event("Draft Saved", user, framework_name, control_name, owner_note[:120] or "Draft saved", evidence_id, role=role)
    return _review_redirect(framework_name, role, user, "Draft saved.", control_name, evidence_id)


@app.post("/evidence/review/cancel")
def evidence_review_cancel(
    framework_name: str = Form(...),
    control_name: str = Form(...),
    evidence_id: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    workflow_cancel(control_name=control_name, framework_name=framework_name, role=role, user=user)
    return RedirectResponse(
        url=f"/framework/{framework_name}?role={role}&user={user}&notice={quote('Draft cancelled.')}",
        status_code=303,
    )


@app.post("/submit")
def submit(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    return_to: str = Form("framework"),
):
    key = control_key(framework_name, control_name)
    if key in approved_controls:
        notice = "Cannot resubmit: observation is closed and auditor approved."
        return _workflow_redirect(role, user, framework_name, return_to, notice)

    was_rejected = key in rejected_controls
    if was_rejected:
        del rejected_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.cancelled_drafts:
        ecs_state.cancelled_drafts.discard(key)
    submitted_controls[key] = "Pending Auditor Review"
    from datetime import datetime, timezone

    ecs_state.submitted_meta[key] = {
        "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "submitted_by": user,
    }
    if key in ecs_state.owner_drafts:
        del ecs_state.owner_drafts[key]
    log_event(
        "Evidence Submitted",
        user,
        framework_name,
        control_name,
        "Submitted to auditor — Pending Auditor Review",
        role=role or "App Owner",
    )

    notice = f"Evidence resubmitted for {control_name}." if was_rejected else f"Submitted {control_name} to auditor review."
    return _workflow_redirect(role, user, framework_name, return_to, notice)


@app.post("/approve")
def approve(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    return_to: str = Form("framework"),
):
    key = control_key(framework_name, control_name)
    from datetime import datetime, timezone

    approved_controls[key] = {
        "status": "Auditor Approved",
        "approved_by": user,
        "approved_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "note": "Observation Closed — Auditor Approved",
    }
    if key in rejected_controls:
        del rejected_controls[key]
    if key in submitted_controls:
        del submitted_controls[key]
    if key in ecs_state.escalated_controls:
        del ecs_state.escalated_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.submitted_meta:
        del ecs_state.submitted_meta[key]
    record_approval(framework_name, control_name, user, "Observation Closed - Auditor Approved")

    return _workflow_redirect(role, user, framework_name, return_to, f"Approved {control_name} — observation closed.")


@app.post("/reject")
def reject(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
    return_to: str = Form("framework"),
):
    reason = reject_reason.strip()
    key = control_key(framework_name, control_name)

    if not reason:
        return _workflow_redirect(role, user, framework_name, return_to, "Reject reason is required.")

    from datetime import datetime, timezone

    rejected_controls[key] = {
        "reason": reason,
        "rejected_by": user,
        "rejected_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "internal": False,
    }
    if key in approved_controls:
        del approved_controls[key]
    if key in submitted_controls:
        del submitted_controls[key]
    if key in ecs_state.escalated_controls:
        del ecs_state.escalated_controls[key]
    if key in ecs_state.clarification_controls:
        del ecs_state.clarification_controls[key]
    if key in ecs_state.submitted_meta:
        del ecs_state.submitted_meta[key]
    record_rejection(framework_name, control_name, user, reason)

    return _workflow_redirect(role, user, framework_name, return_to, f"Rejected {control_name}: {reason}")


@app.post("/workflow/cancel")
def workflow_cancel(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    key = control_key(framework_name, control_name)
    if key in approved_controls:
        return _workflow_redirect(role, user, "", "dashboard", "Cannot cancel a closed observation.")
    ecs_state.cancelled_drafts.add(key)
    if key in submitted_controls:
        del submitted_controls[key]
    log_event("Draft Cancelled", user, framework_name, control_name, "Local draft closed by App Owner")
    return _workflow_redirect(role, user, "", "dashboard", f"Draft cancelled for {control_name}.")


@app.post("/workflow/comment")
def workflow_comment(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    comment: str = Form(...),
):
    key = control_key(framework_name, control_name)
    text = comment.strip()
    if text:
        ecs_state.owner_comments.setdefault(key, []).append({"author": user, "text": text})
        log_event("Owner Comment Added", user, framework_name, control_name, text[:120])
    return _workflow_redirect(role, user, "", "dashboard", "Comment saved to observation record.")


@app.post("/workflow/upload-version")
def workflow_upload_version(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    evidence_id: str = Form(""),
):
    log_event(
        "Evidence Version Uploaded",
        user,
        framework_name,
        control_name,
        f"New version staged for {evidence_id or control_name}",
        evidence_id,
    )
    return _workflow_redirect(
        role, user, "", "dashboard", f"New evidence version uploaded for {control_name} (demo)."
    )


@app.post("/workflow/escalate")
def workflow_escalate(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    key = control_key(framework_name, control_name)
    ecs_state.escalated_controls[key] = {
        "escalated_by": user,
        "reason": "Escalated to compliance leadership for high-risk review.",
    }
    log_event("Observation Escalated", user, framework_name, control_name, "Marked high-risk escalation")
    return _workflow_redirect(role, user, "", "dashboard", f"Escalated {control_name} to leadership queue.")


@app.post("/workflow/clarify")
def workflow_clarify(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    message: str = Form(...),
):
    key = control_key(framework_name, control_name)
    msg = message.strip()
    if key in submitted_controls:
        del submitted_controls[key]
    ecs_state.clarification_controls[key] = {
        "requested_by": user,
        "message": msg,
    }
    if key in ecs_state.escalated_controls:
        del ecs_state.escalated_controls[key]
    if key in ecs_state.submitted_meta:
        del ecs_state.submitted_meta[key]
    log_event("Clarification Requested", user, framework_name, control_name, msg[:120])
    return _workflow_redirect(role, user, "", "dashboard", f"Clarification sent to App Owner for {control_name}.")


@app.post("/workflow/close")
def workflow_close(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
):
    return approve(
        control_name=control_name,
        framework_name=framework_name,
        role=role,
        user=user,
        return_to="dashboard",
    )


@app.post("/workflow/leadership/review")
def workflow_leadership_review(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    action: str = Form("review"),
):
    key = control_key(framework_name, control_name)
    dash_routes = {
        "cio": f"/dashboard/cio?role={role}&user={user}",
        "vertical_head": f"/dashboard/vertical-head?role={role}&user={user}",
        "compliance_head": f"/dashboard/compliance-head?role={role}&user={user}",
        "functional_head": f"/dashboard/functional-head?role={role}&user={user}",
    }
    base = dash_routes.get(role, f"/dashboard?role={role}&user={user}")

    if action in ("approve_closure", "approve"):
        return approve(
            control_name=control_name,
            framework_name=framework_name,
            role=role,
            user=user,
            return_to="dashboard",
        )
    if action == "send_back" or action == "reopen":
        rejected_controls[key] = {
            "reason": f"{role} requested remediation — sent back for App Owner action.",
            "rejected_by": user,
        }
        if key in submitted_controls:
            del submitted_controls[key]
        if key in ecs_state.escalated_controls:
            del ecs_state.escalated_controls[key]
        log_event("Leadership Send Back", user, framework_name, control_name, action)
        return RedirectResponse(url=f"{base}&notice={quote('Observation sent back to App Owner.')}", status_code=303)
    if action == "escalate_governance":
        ecs_state.escalated_controls[key] = {
            "escalated_by": user,
            "reason": "Escalated to enterprise governance board by CIO.",
        }
        log_event("Governance Escalation", user, framework_name, control_name, "CIO escalation")
        return RedirectResponse(url=f"{base}&notice={quote('Escalated to governance board.')}", status_code=303)
    if action == "request_rca":
        ecs_state.clarification_controls[key] = {
            "requested_by": user,
            "message": "CIO requested root cause analysis before closure.",
        }
        if key in submitted_controls:
            del submitted_controls[key]
        log_event("RCA Requested", user, framework_name, control_name, "Executive RCA")
        return RedirectResponse(url=f"{base}&notice={quote('RCA requested from App Owner.')}", status_code=303)

    log_event("Executive Review", user, framework_name, control_name, action)
    return RedirectResponse(url=f"{base}&notice={quote(f'Review logged for {control_name}.')}", status_code=303)


register_mvp_routes(app, templates)

# Idempotent demo bootstrap for reload / TestClient when lifespan already ran
seed_demo_workflow_state()
