# Framework Reference — Mobile Banking Security **[Inferred/Target]**

**Status:** **Not a dedicated key in `FRAMEWORK_CATALOG`.** "Mobile Banking" is a banking **application** (`MOBILE_BANKING_API`) assessed under existing frameworks. Closest shipped coverage: **DPSC** (mobile session security, device binding, channel encryption), **PCI DSS**, **AppSec**, **VAPT**. Documented as a target framework. Part of [Frameworks Library](README.md).

## Purpose
Secure mobile banking channel (app + API) — session, device, transaction, and data protection.

## Objectives
Session security, device binding/fingerprinting, channel encryption, app hardening (root/jailbreak detection), biometric data minimization, API rate limiting.

## Controls (today via DPSC/PCI/AppSec)
Mobile Banking Session Security (DPSC) · Customer Device Binding (DPSC) · UPI/Channel Encryption (DPSC) · Biometric Data Minimization (DPSC) · API rate limiting · App SAST/dependency scan (AppSec). **[Inferred/Target]** dedicated MASVS-style mobile controls.

## Checklist (target)
- [ ] Session timeout + concurrent session audit
- [ ] Device fingerprint enrollment + binding failure analysis
- [ ] TLS/cert pinning on mobile channel
- [ ] Biometric storage audit + consent withdrawal proof
- [ ] Mobile app SAST + dependency scan

## Evidence Requirements
Session configs, device-binding stats, encryption letters, biometric audits, app scan reports.

## Control & Evidence Reuse
Encryption/session/API evidence reuse with **DPSC, PCI DSS, AppSec, VAPT**.

## Reporting / Sample
- **Executive/Audit/Risk:** mobile channel posture via DPSC reporting until dedicated framework added.
- **Sample finding [Inferred]:** missing cert pinning → implement + pentest retest → Approved.
