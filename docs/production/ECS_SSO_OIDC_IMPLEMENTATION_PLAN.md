# ECS SSO / OIDC Implementation Plan

**Mode:** READ-ONLY / ANALYSIS / DOCUMENTATION. **No code changes. No commits.** **Grounding:** `config/auth.yaml`, `app/auth/{providers,jwt_validator,middleware,roles,authz,context,enforcement}.py`, `config/rbac.yaml` (`rbac_catalog`), `config/environments/_base.yaml` (`authentication.sso`).

> **Verified:** ECS already ships an authentication framework. `app/auth/providers.py` registers `azure_ad | oidc | dev`; `jwt_validator.py` validates signature/issuer/audience/exp via JWKS; `middleware.py` enforces auth (secure-by-default, `ECS_AUTH_ENABLED:-true`); `authz.py` PolicyEngine enforces RBAC from `rbac.yaml`. **Production work is configuration + claim→role mapping + validation, with limited (if any) code change.**

---

## 1. Current state
- **Providers:** `azure_ad` (primary), generic `oidc` (Okta/Keycloak/ForgeRock/Entra-as-OIDC), `dev` (bypass, default off).
- **JWT validation:** `allowed_audiences`, `leeway_seconds`, JWKS-based signature, issuer derivation from tenant.
- **Claims mapping (configurable):** `oid`→user_id, `preferred_username`→username, `name`, `email`, `roles`, `groups`.
- **RBAC:** PolicyEngine over `rbac_catalog` (9 canonical roles in `app/auth/roles.py`; alias normalization).
- **Unconfigured:** `tenant_id`/`client_id`/`issuer`/`jwks_uri` blank; `allowed_audiences` blank; SSO slot `ECS_SSO_ENABLED:-false`.

## 2. Azure AD / Entra ID configuration
| Setting | Env var | Source |
|---|---|---|
| Tenant | `ECS_AZURE_TENANT_ID` | Entra tenant GUID |
| Client/App ID | `ECS_AZURE_CLIENT_ID` | App registration |
| Issuer (override) | `ECS_AZURE_ISSUER` | sovereign cloud only |
| JWKS (override) | `ECS_AZURE_JWKS_URI` | derived if blank |
| Audiences | `ECS_AUTH_ALLOWED_AUDIENCES` | API app ID URI |
| Provider | `ECS_AUTH_PROVIDER=azure_ad` | — |
| Auth on | `ECS_AUTH_ENABLED=true` | default |

**App registration:** redirect URIs, expose API scope, **app roles** (or **group claims**) emitted in token; client secret in vault (`ECS_SSO_CLIENT_SECRET`).

## 3. OIDC (generic IdP)
Set `ECS_AUTH_PROVIDER=oidc` + `ECS_OIDC_ISSUER`, `ECS_OIDC_JWKS_URI`, `ECS_OIDC_CLIENT_ID`. Validation path is shared with azure_ad.

## 4. JWT validation
Already enforced: signature (JWKS), `iss`, `aud` (allow-list), `exp`/`nbf` (+leeway). **Verify** in UAT: rejection of wrong-audience, expired, bad-signature tokens (negative tests).

## 5. Role mapping & RBAC mapping
- Token `roles`/`groups` claim → ECS canonical role via `app/auth/roles.normalize_role()` (handles aliases: `owner`→`application_owner`, `admin`/`enterprise_admin`→`system_admin`, etc.).
- **Config gap:** define the **IdP-group/app-role → canonical-role** mapping for the tenant (e.g., AAD group `ECS-Auditors` → `auditor`). Document the mapping table; ensure unmatched → `DEFAULT_ROLE` (`application_owner`, least surprise) and review.
- RBAC permissions/pages already resolved by PolicyEngine from `rbac.yaml`.

**Canonical roles:** cio, auditor, application_owner, compliance_officer, security_officer, vertical_head, functional_head, control_owner, system_admin.

## 6. Session management
Stateless bearer-token model (validate per request). For browser SSO: standard OIDC auth-code flow at the edge/reverse proxy or app login; session cookie carries/refers the token. **Decide & document:** edge-terminated (APIM/oauth2-proxy) vs in-app login. Public paths (`/login`, `/healthz`, `/readyz`, `/static`) bypass auth.

## 7. Logout
- App logout clears local session; **federated logout** redirects to IdP `end_session_endpoint` (Entra logout URL) to terminate the IdP session.
- Document post-logout redirect URI registration.

## 8. Token validation (operational)
JWKS cached + refreshed on rotation; clock skew via `leeway_seconds`; audience allow-list mandatory; reject `dev_mode` in prod (`ECS_AUTH_DEV_MODE` must be false).

## 9. Expected changes
| Type | Change |
|---|---|
| Config | Set Azure/OIDC env vars; `allowed_audiences`; provider; SSO slot |
| Mapping (config/doc) | IdP group/app-role → canonical role table |
| Infra | App registration, vault secret, redirect/logout URIs |
| Code | **Likely none**; possibly small adapter if group→role mapping needs a lookup table beyond alias normalization (~1–2d if required) |

## 10. Effort & risk
| Item | Effort |
|---|---|
| App registration + config | 1 eng-day (+IdP team) |
| Role/group mapping + matrix tests | 1–2 eng-days |
| Session/logout (edge vs in-app) decision + wiring | 1–2 eng-days |
| UAT validation (positive/negative token tests) | 1 eng-day |
| **Total** | **~3–6 eng-days** |

**Risk:** Medium — IdP integration & misconfigured role mapping (over/under-privilege). **Mitigations:** per-role access test matrix; default-least-privilege; staged rollout in UAT with non-prod IdP.

## Cross-references
- [Production Master Plan](../production/ECS_PRODUCTION_READINESS_MASTER_PLAN.md) · [Encryption Plan](../production/ECS_ENCRYPTION_AT_REST_PLAN.md) · [Security Reference](../production/ECS_SECURITY_REFERENCE.md) · [Final Roadmap](../production/ECS_FINAL_PRODUCTION_ROADMAP.md)
