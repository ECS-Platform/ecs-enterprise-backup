"""ECS Audit Intelligence — orchestration & audit-readiness layer.

This package builds the next-generation orchestration and audit-intelligence
capabilities ON TOP OF the (complete) predefined-query platform. It treats the
predefined-query engine, supplementary catalog, and connectors as the execution
layer and derives higher-level structure from them WITHOUT modifying them.

Milestone 1 modules:
  * engines.technology_control_mapping — Technology -> Controls -> Frameworks graph
    derived from the predefined-query catalog (read-only over the engine).
  * engines.asset_discovery            — normalize assets from multiple sources
    (ServiceNow CMDB skeleton, manual import, docker-compose, enterprise GRC CMDB).
  * engines.technology_fingerprint     — deterministic technology/version/criticality
    inference + confidence scoring, cross-linked to applicable controls.

Design principles:
  * Deterministic and offline — no live Docker / DB / network required.
  * Additive — never mutates the predefined-query platform or its data.
  * Serializable dataclasses (see ``models``) for stable API/UI/test surfaces.
"""

from __future__ import annotations

__all__ = ["models"]
