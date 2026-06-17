# ECS Application Configuration Matrix (Phase 4)

Every banking application is configured under `applications.<key>` in the
environment schema (`host` / `port` / `base_url` / `business_unit` /
`criticality` / `enabled`). The table shows the YAML key and the shipped UAT vs
PROD defaults (override via the matching `APP_*` env var or by editing the env
file).

| Application | Module Usage | YAML Section | UAT default (`uat.yaml`) | PROD default (`prod.yaml`) |
|-------------|--------------|--------------|--------------------------|-----------------------------|
| Net Banking | Application Inventory, Evidence, Dashboards | `applications.netbanking` | `netbanking.uat.bank.local:443` | `netbanking.bank.com:443` |
| Mobile Banking | Application Inventory, Evidence | `applications.mobilebanking` | `mobile.uat.bank.local:443` | `mobile.bank.com:443` |
| Payments | Application Inventory, Evidence, AppSec | `applications.payments` | `payments.uat.bank.local:443` | `payments.bank.com:443` |
| CBS (Core Banking) | Application Inventory, Infrastructure | `applications.cbs` | `cbs.uat.bank.local:443` | `cbs.bank.com:443` |
| UPI | Application Inventory, Payments | `applications.upi` | `upi.uat.bank.local:443` | `upi.bank.com:443` |
| LOS (Loan Origination) | Application Inventory | `applications.los` | `${APP_LOS_HOST}:443` | `${APP_LOS_HOST}:443` |
| LMS (Loan Management) | Application Inventory | `applications.lms` | `${APP_LMS_HOST}:443` | `${APP_LMS_HOST}:443` |
| CRM | Application Inventory | `applications.crm` | `${APP_CRM_HOST}:443` | `${APP_CRM_HOST}:443` |
| Treasury | Application Inventory | `applications.treasury` | `${APP_TREASURY_HOST}:443` | `${APP_TREASURY_HOST}:443` |
| Cards | Application Inventory | `applications.cards` | `${APP_CARDS_HOST}:443` | `${APP_CARDS_HOST}:443` |
| Trade Finance | Application Inventory | `applications.trade_finance` | `${APP_TRADEFIN_HOST}:443` | `${APP_TRADEFIN_HOST}:443` |
| Merchant Acquiring | Application Inventory, Payments | `applications.merchant_acquiring` | `${APP_MERCHANT_HOST}:443` | `${APP_MERCHANT_HOST}:443` |
| API Gateway | Infrastructure, Connectors | `applications.api_gateway` | `${APP_APIGW_HOST}:443` | `${APP_APIGW_HOST}:443` |
| Middleware | Infrastructure, Baselining | `applications.middleware` | `${APP_MIDDLEWARE_HOST}:8443` | `${APP_MIDDLEWARE_HOST}:8443` |
| Authentication Services | Infrastructure, SSO | `applications.authentication_services` | `${APP_AUTHSVC_HOST}:443` | `${APP_AUTHSVC_HOST}:443` |

> Applications without an explicit per-env host inherit the `_base.yaml`
> integration slot (`${APP_*_HOST:-}`); set the corresponding `APP_*_HOST` /
> `APP_*_URL` env var or edit the env file to activate them in UAT/PROD.

## Validation

`get_application(<key>)` returns the resolved record in every environment;
`applications` contains all 15 keys in `local`, `dev`, `sit`, `uat`, and `prod`
(verified). Each application’s `criticality` and `business_unit` are inherited
from `_base.yaml` and drive risk weighting in dashboards.
