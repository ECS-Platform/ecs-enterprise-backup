"""ECS functional-test automation framework (reusable capability library).

Nothing in this package fakes ECS: every helper drives the real ECS HTTP surface, PostgreSQL schema,
object store, scheduler and audit trail that exist in this repository. Where ECS does not expose a
capability, helpers raise ``CapabilityBlocked`` (reported as a skip with a reason) instead of inventing one.
"""
