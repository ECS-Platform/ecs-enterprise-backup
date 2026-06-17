# Framework Reference — Nginx Baselining

**Grounding:** `framework_catalog._nginx_catalog()`, route `/framework/Nginx Baselining`, Nginx predefined queries. **Status:** Catalog framework. Part of [Frameworks Library](README.md).

## Purpose
Harden Nginx edge/reverse-proxy tiers (e.g., `NGINX_EDGE_DMZ_01`) for banking front doors.

## Objectives
TLS configuration, secure headers, cipher policy, access/rate limiting, logging, version/patch hygiene.

## Controls (catalog, sample)
TLS protocol/cipher enforcement · Secure headers (HSTS/CSP) · Request rate limiting · Access logging · Server tokens off / version hardening · Reverse-proxy timeouts.

## Checklist (sample)
- [ ] TLS 1.2+ only, weak ciphers disabled
- [ ] HSTS + security headers present
- [ ] Rate limiting configured at edge
- [ ] Access/error logging enabled + shipped to SIEM
- [ ] `server_tokens off`

## Evidence Requirements
`nginx.conf` exports, TLS scan output, header check results. **Query-driven** via Nginx connector.

## Control & Evidence Reuse
TLS/header/rate-limit evidence reuse with **PCI DSS (TLS), AppSec, Cloud Security**.

## Reporting
- **Executive:** edge hardening posture.
- **Audit:** Nginx config compliance pack.
- **Risk:** weak TLS/missing headers to Risk Register.

## Sample Assessment / Findings / Closure
- **Assessment:** TLS config within scope (matches PCI TLS evidence).
- **Finding:** missing HSTS header on one vhost.
- **Closure:** config update + re-scan → Approved.
