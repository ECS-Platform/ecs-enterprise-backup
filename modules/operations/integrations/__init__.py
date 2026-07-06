"""ECS enterprise integration skeletons (config-driven; no real calls in tests).

Currently ships integration *skeletons* only:
  * servicenow_cmdb — ServiceNow CMDB asset/CI fetch interface + mapping stubs.
  * archer          — Archer control/framework fetch interface + mapping stubs.

Both are credential-externalised, never log secrets, and accept an injectable
transport so unit tests can supply mocked responses without any network access.
"""
