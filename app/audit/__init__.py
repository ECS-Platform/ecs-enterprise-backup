"""ECS durable audit foundation (Phase 4, Step 1).

Provides a central, durable audit write API (AuditService) over the PostgreSQL
audit_log table. This is FOUNDATION ONLY — no workflow, approval, observation,
dashboard, RBAC, or RAG code is wired to it yet. Importing this package changes
no ECS behavior.
"""

from app.audit.service import AuditService, AuditRecord, new_request_id

__all__ = ["AuditService", "AuditRecord", "new_request_id"]
