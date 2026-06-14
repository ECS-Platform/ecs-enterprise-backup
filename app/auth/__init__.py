"""ECS authentication foundation (Phase 1).

Pluggable enterprise authentication (Azure AD / OIDC / JWT) that establishes a
trusted, server-validated user identity. This package handles AUTHENTICATION
ONLY — it never makes authorization (RBAC) decisions. Roles/groups carried on
the authenticated principal are passed through for later RBAC phases.

Public surface:
    AuthenticatedUser          - the user-context model
    get_current_principal      - FastAPI dependency returning the current user
    AuthenticationError        - raised on auth failures (mapped to 401/403)
    register_authentication    - install middleware on the FastAPI app
"""

from app.auth.context import (
    AuthenticatedUser,
    current_principal,
    get_current_principal,
)
from app.auth.enforcement import (
    enforce_page,
    enforce_permission,
    rbac_enforcement_enabled,
    resolve_effective_role,
)
from app.auth.errors import AuthenticationError
from app.auth.middleware import register_authentication
from app.auth.mutation_guard import (
    guard_mutation,
    mutation_enforcement_enabled,
)
from app.auth.page_guard import (
    can_view_page,
    guard_page,
    page_enforcement_enabled,
)
from app.auth.scope import (
    apply_scope,
    resolve_assignments,
    resolve_scope,
    scope_filter,
    scope_filtering_enabled,
    scope_sql,
)

__all__ = [
    "AuthenticatedUser",
    "AuthenticationError",
    "current_principal",
    "get_current_principal",
    "register_authentication",
    # Phase 2 Step 2B — RBAC enforcement foundation.
    "resolve_effective_role",
    "enforce_permission",
    "enforce_page",
    "rbac_enforcement_enabled",
    # Phase 2 Step 2D-critical — critical-mutation authorization guard.
    "guard_mutation",
    "mutation_enforcement_enabled",
    # Phase 2 Step 2C — dashboard / page authorization guard.
    "guard_page",
    "can_view_page",
    "page_enforcement_enabled",
    # Phase 2 Step 3 — data scope filtering.
    "resolve_scope",
    "resolve_assignments",
    "scope_filter",
    "apply_scope",
    "scope_sql",
    "scope_filtering_enabled",
]
