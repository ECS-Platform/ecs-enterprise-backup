"""Centralized Operations module catalog — applications, frameworks, owners, control domains."""

from __future__ import annotations

ALL_FRAMEWORKS = [
    "PCI DSS", "DPSC", "OS Baselining", "DB Baselining", "Nginx Baselining",
    "AppSec", "VAPT", "CSITE", "ITPP",
]

BANKING_APPLICATIONS = [
    "Net Banking", "Mobile Banking", "UPI", "Treasury", "Wealth Portal",
    "Loan Origination", "Credit Card Switch", "Core Banking", "Internet Banking",
    "Merchant Portal", "ATM Switch", "Payments Hub", "Trade Finance", "FX Platform",
    "Retail LOS", "Corporate Banking", "AML Engine", "Fraud Monitoring",
    "Reconciliation Hub", "CRM Platform", "Card Platform", "Payments",
    "UPI Gateway", "Internet Banking Edge", "Wealth Management",
]

OWNERS = [
    "R. Mehta", "A. Sharma", "S. Banerjee", "K. Iyer", "P. Rao",
    "M. Khanna", "N. Verma", "T. Joseph",
]

RISKS = ["Critical", "High", "Medium", "Low"]

APP_OWNER_MAP: dict[str, str] = {
    "Net Banking": "R. Mehta",
    "Mobile Banking": "A. Sharma",
    "UPI": "P. Rao",
    "Treasury": "A. Sharma",
    "Wealth Portal": "V. Rao",
    "Loan Origination": "V. Rao",
    "Credit Card Switch": "R. Mehta",
    "Core Banking": "A. Sharma",
    "Internet Banking": "A. Sharma",
    "Merchant Portal": "K. Iyer",
    "ATM Switch": "M. Khanna",
    "Payments Hub": "K. Iyer",
    "Trade Finance": "N. Verma",
    "FX Platform": "T. Joseph",
    "Retail LOS": "V. Rao",
    "Corporate Banking": "R. Mehta",
    "AML Engine": "S. Banerjee",
    "Fraud Monitoring": "S. Banerjee",
    "Reconciliation Hub": "K. Iyer",
    "CRM Platform": "N. Verma",
    "Card Platform": "R. Mehta",
    "Payments": "K. Iyer",
    "UPI Gateway": "P. Rao",
    "Internet Banking Edge": "A. Sharma",
    "Wealth Management": "N. Verma",
}

# Fix V. Rao -> P. Rao per user spec (user listed P. Rao not V. Rao)
APP_OWNER_MAP["Wealth Portal"] = "P. Rao"
APP_OWNER_MAP["Loan Origination"] = "P. Rao"
APP_OWNER_MAP["Retail LOS"] = "P. Rao"

FRAMEWORK_EVIDENCE: dict[str, list[str]] = {
    "PCI DSS": ["Firewall exports", "MFA enrollment", "SIEM log review", "Segmentation test", "Encryption attestation"],
    "DPSC": ["Consent logs", "Data retention policy", "PII inventory", "Privacy impact assessment"],
    "OS Baselining": ["CIS hardening scan", "Linux patch baseline", "Tripwire integrity report", "Windows baseline"],
    "DB Baselining": ["Oracle hardening", "DB encryption report", "Privileged DB access review", "Audit logging"],
    "Nginx Baselining": ["TLS configuration", "WAF baseline", "Reverse proxy access logs"],
    "AppSec": ["SAST report", "Dependency scan", "Secure SDLC attestation", "Secrets scan"],
    "VAPT": ["External VA scan", "Pen-test report", "CVE remediation", "Retest evidence"],
    "CSITE": ["Access review certification", "SIEM use-case export", "Incident response drill"],
    "ITPP": ["DR drill evidence", "BCP test attestation", "Recovery time mapping"],
}

FRAMEWORK_CONTROLS: dict[str, list[str]] = {
    "PCI DSS": ["PCI-7.2", "PCI-8.3", "PCI-10.6", "PCI-11.3"],
    "DPSC": ["DP-C-04", "DP-C-07", "DP-C-09"],
    "OS Baselining": ["OSB-11", "OSB-14", "OSB-18"],
    "DB Baselining": ["DBB-03", "DBB-06", "DBB-09"],
    "Nginx Baselining": ["NGX-02", "NGX-05", "NGX-08"],
    "AppSec": ["APPSEC-9", "APPSEC-12", "APPSEC-15"],
    "VAPT": ["VAPT-4", "VAPT-7", "VAPT-9"],
    "CSITE": ["CS-C-03", "CS-C-05", "CS-C-08"],
    "ITPP": ["ITPP-DR-02", "ITPP-BCP-05", "ITPP-REC-03"],
}

CONNECTORS_BY_FRAMEWORK: dict[str, list[str]] = {
    "PCI DSS": ["SharePoint", "ServiceNow", "Splunk", "Prisma"],
    "DPSC": ["Confluence", "OneTrust", "SharePoint"],
    "OS Baselining": ["Tripwire", "ServiceNow CMDB", "Prisma", "BMC Helix CMDB"],
    "DB Baselining": ["Prisma", "BMC Helix CMDB", "ServiceNow"],
    "Nginx Baselining": ["Tripwire", "Prisma", "Splunk"],
    "AppSec": ["SonarQube", "Checkmarx", "Jira"],
    "VAPT": ["Jira", "SonarQube", "Qualys"],
    "CSITE": ["Splunk", "ServiceNow GRC", "Prisma"],
    "ITPP": ["SharePoint", "ServiceNow GRC", "Tripwire"],
}

MODULE_STATUSES: dict[str, list[str]] = {
    "scheduler": ["Running", "Failed", "Partial", "Delayed", "Completed", "Success"],
    "upload": ["Uploaded", "Validating", "Rejected", "Approved", "Pending Review", "Expired"],
    "integrations": ["Healthy", "Partial", "Failed", "Pending Setup", "Retry Pending", "Auth Expired", "Sync Delayed"],
    "onboarding": ["In Progress", "Completed", "Pending Mapping", "Failed Discovery", "Production"],
}


def owner_for(app: str) -> str:
    return APP_OWNER_MAP.get(app, OWNERS[hash(app) % len(OWNERS)])
