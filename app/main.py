
from urllib.parse import quote

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="ECS Consolidated Demo V13")

templates = Jinja2Templates(directory="app/templates")

frameworks = {
    "PCI DSS": [
        ("Encryption at Rest", "Database Encryption Report"),
        ("Encryption in Transit", "TLS Config Evidence"),
        ("MFA Enabled", "IAM MFA Screenshot"),
        ("Firewall Rules", "Firewall Export"),
        ("VAPT Completed", "PCI VAPT Report"),
        ("SIEM Monitoring", "SOC Dashboard"),
        ("DR Enabled", "DR Drill Report"),
        ("Key Rotation", "Key Rotation Report"),
        ("Access Review", "Access Review Evidence"),
        ("Audit Logs", "Audit Log Export")
    ],
    "DPSC": [
        ("API Security", "API Gateway Config"),
        ("Fraud Monitoring", "Fraud Dashboard"),
        ("UPI Encryption", "UPI Encryption Report"),
        ("Card Tokenization", "Tokenization Report"),
        ("Log Monitoring", "Centralized Logs")
    ],
    "OS Baselining": [
        ("Linux Hardening", "OS Hardening Checklist"),
        ("SSH Restrictions", "SSH Config"),
        ("AV Enabled", "AV Dashboard"),
        ("Patch Compliance", "Patch Report")
    ],
    "DB Baselining": [
        ("Password Rotation", "Password Rotation Report"),
        ("Audit Logging", "DB Audit Logs"),
        ("Backup Configured", "Backup Report"),
        ("DB Encryption", "Database Encryption")
    ],
    "Nginx Baselining": [
        ("TLS 1.2 Enabled", "Nginx TLS Config"),
        ("HTTP Disabled", "HTTP Redirect Config"),
        ("Secure Headers", "Security Header Evidence"),
        ("WAF Enabled", "WAF Dashboard")
    ],
    "CSITE": [
        ("SOC Monitoring", "SOC Dashboard"),
        ("Threat Detection", "Threat Intel Report"),
        ("EDR Enabled", "EDR Console"),
        ("SIEM Alerts", "SIEM Alert Screenshot")
    ]
}

submitted_controls = {}
approved_controls = {}
rejected_controls = {}


def control_key(framework_name: str, control_name: str) -> str:
    return f"{framework_name}::{control_name}"

scheduler_data = [
    ("Net Banking", "PCI DSS", "Implemented"),
    ("Mobile Banking", "DPSC", "Partial"),
    ("Payments", "Nginx Baselining", "Implemented"),
    ("UPI", "OS Baselining", "Implemented")
]

def chatbot_answer(query):
    q = query.lower()

    if "pci" in q:
        return "PCI DSS framework has 10 evidences mapped with encryption, MFA, VAPT and audit logging controls."

    if "dpsc" in q:
        return "DPSC framework includes API security, fraud monitoring and tokenization controls."

    if "baselining" in q:
        return "OS, DB and Nginx baselining evidences are available and mapped."

    if "audit" in q:
        return "Audit evidence tracking is enabled across all frameworks."

    if "reject" in q or "rejection" in q or "reason" in q:
        if not rejected_controls:
            return "No rejected evidences at the moment. Auditors can reject submitted controls with a mandatory reason."

        lines = []
        for key, info in list(rejected_controls.items())[:8]:
            _framework, control = key.split("::", 1)
            lines.append(f"{control} ({_framework}): {info['reason']}")
        return "Rejected evidences and reasons — " + " | ".join(lines)

    return f"ECS AI processed query successfully: {query}"

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={}
    )

@app.post("/login")
def login(role: str = Form(...)):
    user = "AppOwner" if role == "owner" else "Auditor"

    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}",
        status_code=303
    )

@app.get("/logout")
def logout():
    return RedirectResponse("/", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    role: str = "owner",
    user: str = "User",
    response: str = ""
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "frameworks": frameworks.keys(),
            "scheduler_data": scheduler_data,
            "role": role,
            "user": user,
            "response": response,
            "rejected_controls": rejected_controls,
        }
    )

@app.post("/chat")
def chat(
    query: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    framework_name: str = Form(""),
):

    response = chatbot_answer(query)
    encoded = quote(response)

    if framework_name:
        return RedirectResponse(
            url=f"/framework/{framework_name}?role={role}&user={user}&response={encoded}",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/dashboard?role={role}&user={user}&response={encoded}",
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
    return templates.TemplateResponse(
        request=request,
        name="framework.html",
        context={
            "framework_name": framework_name,
            "frameworks": frameworks.keys(),
            "controls": frameworks.get(framework_name, []),
            "role": role,
            "user": user,
            "response": response,
            "notice": notice,
            "submitted_controls": submitted_controls,
            "approved_controls": approved_controls,
            "rejected_controls": rejected_controls,
        }
    )

@app.post("/submit")
def submit(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...)
):

    key = control_key(framework_name, control_name)
    was_rejected = key in rejected_controls
    if was_rejected:
        del rejected_controls[key]
    submitted_controls[key] = "Submitted To Auditor"

    url = f"/framework/{framework_name}?role={role}&user={user}"
    if was_rejected:
        url += f"&notice={quote(f'Evidence resubmitted for {control_name}.')}"
    return RedirectResponse(url=url, status_code=303)

@app.post("/approve")
def approve(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...)
):

    key = control_key(framework_name, control_name)
    approved_controls[key] = "Approved"
    if key in rejected_controls:
        del rejected_controls[key]

    return RedirectResponse(
        url=f"/framework/{framework_name}?role={role}&user={user}",
        status_code=303,
    )

@app.post("/reject")
def reject(
    control_name: str = Form(...),
    framework_name: str = Form(...),
    role: str = Form(...),
    user: str = Form(...),
    reject_reason: str = Form(...),
):
    reason = reject_reason.strip()
    key = control_key(framework_name, control_name)

    if not reason:
        notice = quote("Reject reason is required.")
        return RedirectResponse(
            url=f"/framework/{framework_name}?role={role}&user={user}&notice={notice}",
            status_code=303,
        )

    rejected_controls[key] = {
        "reason": reason,
        "rejected_by": user,
    }
    if key in approved_controls:
        del approved_controls[key]
    if key in submitted_controls:
        del submitted_controls[key]

    notice = quote(f"Rejected {control_name}: {reason}")
    return RedirectResponse(
        url=f"/framework/{framework_name}?role={role}&user={user}&notice={notice}",
        status_code=303,
    )
