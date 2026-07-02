"""ECS durable observation persistence (Phase 4, Step 3).

Promotes observations to a first-class durable entity backed by the PostgreSQL
`observations` table, WITHOUT redesigning the in-memory model that dashboards and
workflows read today. The store is a write-through, best-effort durability layer:

  * Gated by OBSERVATIONS_DURABLE_ENABLED (default FALSE) -> every function is a
    no-op and existing ECS behavior is byte-for-byte unchanged.
  * When enabled, observation create/update/close/reopen mutations are mirrored to
    Postgres so they survive application / container / server restart and DB
    reconnect, and a startup hydration reloads them back into in-memory state.
  * Never raises: a DB problem can never break a workflow request.

Importing this package changes no ECS behavior.
"""

from app.observations.store import (
    durable_observations_enabled,
    persist_observation,
    persist_close,
    persist_reopen,
    hydrate_into_memory,
    migrate_memory_to_durable,
)

__all__ = [
    "durable_observations_enabled",
    "persist_observation",
    "persist_close",
    "persist_reopen",
    "hydrate_into_memory",
    "migrate_memory_to_durable",
]
