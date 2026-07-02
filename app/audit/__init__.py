"""ECS durable audit foundation (Phase 4).

Step 1 provides the central durable write API (AuditService) over the PostgreSQL
audit_log table. Step 2 adds workflow audit wiring (audit_workflow_action), gated
by AUDIT_WORKFLOW_ENABLED (default FALSE) so existing ECS behavior is unchanged
until explicitly enabled.
"""

from app.audit.service import AuditService, AuditRecord, new_request_id
from app.audit.workflow import audit_workflow_action, workflow_audit_enabled

__all__ = [
    "AuditService",
    "AuditRecord",
    "new_request_id",
    "audit_workflow_action",
    "workflow_audit_enabled",
]
