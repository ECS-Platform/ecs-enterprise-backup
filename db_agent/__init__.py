"""ECS DB Agent — PROTOTYPE.

A small, self-contained agent intended to run on a jump server inside a secured
internal bank network during prototype / UAT. It executes database and host
(SSH) connectivity checks using SIMPLE CONFIGURATION ONLY.

>>> THIS IS A PROTOTYPE. THIS IS NOT PRODUCTION SECURE. <<<

The DB Agent deliberately has NO dependency on enterprise security
infrastructure (mTLS, JWT, OIDC, OAuth, Vault, PKI/certificates, SSO, Azure AD,
Keycloak, HSM). The absence of any of those MUST NEVER prevent the agent from
starting. All such features are OPTIONAL, OFF BY DEFAULT extension points (see
``db_agent.security``).

This package is independent of the ECS platform's own security framework and
must not modify, weaken, or disable it. It only reuses ECS's existing database
connectors for execution.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0-prototype"
