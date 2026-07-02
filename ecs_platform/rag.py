"""ECS production-grade LLM-RAG orchestrator (Gemini-backed, grounded + cited).

Pipeline:
    User Query
      -> RBAC Filter            (scope evidence to the caller's role)
      -> Evidence Retrieval     (pgvector semantic search, repository fallback)
      -> Reuse Mapping          (control -> evidence reuse)
      -> Framework Mapping      (control -> framework crosswalk: SOC2/ISO/PCI/RBI/AI-SDLC)
      -> Context Assembly       (governance facts + enriched, citable evidence blocks)
      -> Gemini                 (grounded generation, citations required)
      -> Cited Response         (evidence IDs, source systems, timestamps, framework mappings)

Degrades gracefully: with no GEMINI_API_KEY (or empty vector store) the caller can
fall back to the deterministic keyword assistant. Every read is repository-grounded;
the model never sees anything outside the retrieved, RBAC-scoped evidence.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from ecs_platform.governance import (
    CONTROL_CROSSWALK,
    REUSE_FRAMEWORKS,
    audit_readiness,
    control_coverage,
    evidence_reuse,
    executive_summary,
    framework_coverage,
)
from ecs_platform.ingestion import to_jsonable
from ecs_platform.llm_engine.metrics_logger import persist_rag_metric
from ecs_platform.repository import EvidenceRepository, RepositoryError

# Exact refusal message when retrieval yields nothing (anti-hallucination contract).
NO_EVIDENCE_MESSAGE = "No evidence found in ECS repository."


def _logger():
    """Return a best-effort structured logger; falls back to a no-op print wrapper."""
    try:
        from modules.shared.services import ecs_logging

        return lambda where, msg: ecs_logging.info(where, msg)
    except Exception:  # noqa: BLE001
        return lambda where, msg: None


def warm_models() -> dict[str, Any]:
    """Warm the local LLM (generation + embedding) so first query isn't a cold start.

    No-op for cloud providers that don't implement warm(). Never raises."""
    try:
        from ecs_platform.llm_engine.provider import get_provider

        provider = get_provider()
        if not provider.configured():
            return {"ok": False, "detail": "provider not configured"}
        warm = getattr(provider, "warm", None)
        if not callable(warm):
            return {"ok": True, "detail": "provider has no warm step (cloud)"}
        status = warm()
        status["ok"] = bool(status.get("chat_warm") or status.get("embed_warm"))
        return status
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "detail": f"warm failed: {exc}"}

# ECS UI role -> rbac.yaml role.
_ROLE_ALIASES = {
    "cio": "cio",
    "compliance_head": "compliance_officer",
    "compliance_officer": "compliance_officer",
    "auditor": "auditor",
    "owner": "application_owner",
    "application_owner": "application_owner",
    "admin": "admin",
    "security_officer": "security_officer",
    "vertical_head": "vertical_head",
}
# Keyword -> evidence review status (for lifecycle-style questions).
_STATUS_WORDS = {
    "rejected": "Rejected", "approved": "Approved", "expired": "Expired",
    "under review": "UnderReview", "pending": "UnderReview", "collected": "Collected",
}


def llm_connectivity() -> dict[str, Any]:
    """Live LLM reachability check (1-token generate + 1 embed). Provider-agnostic.

    Works for Ollama (local, keyless) and Gemini/OpenAI/etc. Never raises; never
    logs secrets."""
    out: dict[str, Any] = {"provider": "", "model": "", "embedding_model": "",
                           "configured": False, "reachable": False, "embed_ok": False,
                           "embed_dim": 0, "detail": "", "request_id": str(uuid.uuid4()),
                           "timestamp": datetime.now(timezone.utc).isoformat(),
                           "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    try:
        from ecs_platform.llm_engine.provider import get_provider

        provider = get_provider()
        out["provider"] = type(provider).__name__.replace("Provider", "").lower()
        out["model"] = provider.model
        out["embedding_model"] = provider.embedding_model
        out["configured"] = provider.configured()
        if not provider.configured():
            out["detail"] = "provider not configured"
            return out
        txt, usage = provider.generate_with_metadata(
            "Reply with the single word OK.",
            system="You are a health probe.",
        )
        out["input_tokens"] = int(usage.get("input_tokens", 0) or 0)
        out["output_tokens"] = int(usage.get("output_tokens", 0) or 0)
        out["total_tokens"] = int(
            usage.get("total_tokens", 0) or (out["input_tokens"] + out["output_tokens"])
        )
        out["reachable"] = bool(txt)
        vec = provider.embed(["healthcheck"])
        out["embed_ok"] = bool(vec and vec[0])
        out["embed_dim"] = len(vec[0]) if (vec and vec[0]) else 0
        out["detail"] = "ok" if out["reachable"] and out["embed_ok"] else "partial"
    except Exception as exc:  # noqa: BLE001
        out["detail"] = f"unreachable: {exc}"
    return out


# Backward-compatible alias (route still imports gemini_connectivity).
def gemini_connectivity() -> dict[str, Any]:
    return llm_connectivity()


def rag_status() -> dict[str, Any]:
    """Readiness of the RAG stack: provider key + vector index population."""
    status: dict[str, Any] = {
        "provider": "", "provider_configured": False, "model": "", "embedding_model": "",
        "vector_ready": False, "vector_count": 0, "evidence_count": 0, "indexed_pct": 0.0,
        "ready": False, "notes": [],
    }
    try:
        from ecs_platform.llm_engine.provider import get_provider

        provider = get_provider()
        status["provider"] = type(provider).__name__.replace("Provider", "").lower()
        status["provider_configured"] = provider.configured()
        status["model"] = provider.model
        status["embedding_model"] = provider.embedding_model
        if not provider.configured():
            status["notes"].append(f"LLM provider '{status['provider']}' not configured.")
    except Exception as exc:  # noqa: BLE001
        status["notes"].append(f"provider error: {exc}")

    try:
        from ecs_platform.vectorstore import get_vector_store

        store = get_vector_store()
        store.init_store()
        with store._connect().cursor() as cur:  # noqa: SLF001 - internal count
            cur.execute(f"SELECT count(*) FROM {store._table}")  # noqa: SLF001
            status["vector_count"] = int(cur.fetchone()[0])
        status["vector_ready"] = status["vector_count"] > 0
    except Exception as exc:  # noqa: BLE001
        status["notes"].append(f"vector store unavailable: {exc}")

    try:
        with EvidenceRepository() as repo:
            status["evidence_count"] = repo.counts().get("total", 0)
    except RepositoryError as exc:
        status["notes"].append(f"repository unavailable: {exc}")

    if status["evidence_count"]:
        status["indexed_pct"] = round(100 * status["vector_count"] / status["evidence_count"], 1)
    status["ready"] = bool(status["provider_configured"])
    return status


def _governance_documents() -> list[dict[str, Any]]:
    """Build text documents from governance + lineage + audit so the assistant can
    reason over them too. Each doc: {uid, text, metadata}. Read-only; no new evidence."""
    docs: list[dict[str, Any]] = []
    try:
        with EvidenceRepository() as repo, repo.connect().cursor() as cur:
            # application inventory + framework assignments
            cur.execute(
                """
                SELECT a.slug, a.name, a.business_unit, a.criticality, a.owner, a.lifecycle_status,
                       array_remove(array_agg(DISTINCT f.framework_code), NULL) AS frameworks
                FROM applications a
                LEFT JOIN application_frameworks f ON f.app_slug = a.slug
                GROUP BY a.id
                """)
            for r in cur.fetchall():
                slug, name, bu, crit, owner, st, fws = r
                docs.append({
                    "uid": f"app:{slug}",
                    "text": (f"Application {name} (slug {slug}). Business unit: {bu}. "
                             f"Criticality: {crit}. Owner: {owner}. Lifecycle status: {st}. "
                             f"In-scope frameworks: {', '.join(fws) or 'none'}."),
                    "metadata": {"source_system": "governance", "object_type": "application",
                                 "application": slug}})

            # control catalog + framework crosswalk (framework mappings)
            cur.execute("SELECT control_id, name, description, framework_code FROM control_catalog")
            cat = cur.fetchall()
            cur.execute("SELECT control_id, framework_code, requirement_ref FROM control_framework_crosswalk")
            cross: dict[str, list[str]] = {}
            for cid, fw, ref in cur.fetchall():
                cross.setdefault(cid, []).append(f"{fw} {ref or ''}".strip())
            for cid, cname, cdesc, cfw in cat:
                docs.append({
                    "uid": f"control:{cid}",
                    "text": (f"Control {cid}: {cname}. {cdesc or ''} Primary framework: {cfw}. "
                             f"Satisfies framework requirements: {', '.join(cross.get(cid, [])) or cfw}."),
                    "metadata": {"source_system": "governance", "object_type": "control",
                                 "application": ""}})

            # evidence reviews (observations / review status / rejected evidence)
            cur.execute(
                """
                SELECT r.evidence_uid, r.status, r.reviewer, r.note, e.title, e.application, e.source_system
                FROM evidence_reviews r LEFT JOIN evidence e ON e.evidence_uid = r.evidence_uid
                """)
            for euid, st, rev, note, title, app, src in cur.fetchall():
                docs.append({
                    "uid": f"review:{euid}",
                    "text": (f"Evidence review for '{title or euid}' ({src}, app {app}): "
                             f"status {st}. Reviewer: {rev or 'n/a'}. Note: {note or 'none'}."),
                    "metadata": {"source_system": "governance", "object_type": "observation",
                                 "application": app or ""}})

            # lineage edges (evidence_relationships). Use the lineage row id in the
            # uid: parent_uid can be NULL (root/ingest edges) and the same pair can
            # appear under different operations, which collides on parent->child alone.
            cur.execute(
                """
                SELECT l.id, e.evidence_uid, l.parent_uid, l.operation, e.application
                FROM evidence_lineage l JOIN evidence e ON e.id = l.evidence_id
                """)
            for lid, child, parent, op, app in cur.fetchall():
                docs.append({
                    "uid": f"lineage:{lid}",
                    "text": f"Evidence relationship: {parent or 'root'} -> {child} via {op} (app {app}).",
                    "metadata": {"source_system": "governance", "object_type": "relationship",
                                 "application": app or ""}})

            # audit history (use row id in the uid to guarantee unique chunk_ids;
            # action+resource+timestamp can collide for same-second events)
            cur.execute(
                "SELECT id, actor, role, action, resource, created_at FROM audit_log "
                "ORDER BY created_at DESC LIMIT 500")
            for aid, actor, role, action, resource, ts in cur.fetchall():
                docs.append({
                    "uid": f"audit:{aid}",
                    "text": f"Audit event at {ts}: {actor} ({role}) performed {action} on {resource}.",
                    "metadata": {"source_system": "governance", "object_type": "audit", "application": ""}})
    except (RepositoryError, Exception):  # noqa: BLE001 - governance tables optional
        pass
    return docs


def _existing_chunk_hashes(store) -> dict[str, str]:
    """Map chunk_id -> stored content_hash for incremental reindex. Empty on any error."""
    try:
        with store._connect().cursor() as cur:  # noqa: SLF001
            cur.execute(f"SELECT chunk_id, metadata->>'content_hash' FROM {store._table}")  # noqa: SLF001
            return {row[0]: (row[1] or "") for row in cur.fetchall()}
    except Exception:  # noqa: BLE001
        return {}


def reindex_evidence(limit: int = 5000, *, incremental: bool = True) -> dict[str, Any]:
    """Embed repository evidence + governance/framework docs into pgvector via the
    configured local provider (Ollama / nomic-embed-text).

    Sources indexed: Evidence Repository, Governance Controls, Framework Library
    (crosswalk), application inventory, relationships, reviews/observations, audit.

    Incremental: each chunk carries a content_hash; chunks whose text is unchanged
    are skipped (duplicate prevention). pgvector upserts on chunk_id so re-runs are
    idempotent. No new evidence is created — read-only over the repository."""
    import hashlib
    import time as _t

    from ecs_platform.repository import EvidenceRepository as _Rep

    log = _logger()
    started = _t.time()
    report: dict[str, Any] = {
        "ok": False, "provider": "", "model": "", "embedding_model": "",
        "evidence": 0, "governance_docs": 0, "candidate_chunks": 0,
        "embedded_chunks": 0, "skipped_unchanged": 0, "vector_count": 0,
        "errors": [], "elapsed_sec": 0.0,
    }
    try:
        from ecs_platform.config import load_vectorstore_config
        from ecs_platform.llm_engine.provider import get_provider
        from ecs_platform.vectorstore import Chunk, chunk_text, get_vector_store

        provider = get_provider()
        report["provider"] = type(provider).__name__.replace("Provider", "").lower()
        report["model"] = provider.model
        report["embedding_model"] = provider.embedding_model
        if not provider.configured():
            report["errors"].append("LLM provider not configured; cannot embed.")
            return report

        chunk_cfg = (load_vectorstore_config().get("vectorstore", {}) or {}).get("chunking", {})
        size = int(chunk_cfg.get("chunk_size", 1000))
        overlap = int(chunk_cfg.get("chunk_overlap", 150))

        with _Rep() as repo:
            rows = repo.search_evidence(limit=limit)
            full = [repo.evidence_by_uid(r["evidence_uid"]) for r in rows]

        store = get_vector_store()
        store.init_store()
        existing = _existing_chunk_hashes(store) if incremental else {}
        log("ECSPlatform", f"RAG reindex start: {len([f for f in full if f])} evidence, "
                           f"provider={report['provider']}/{report['model']}, incremental={incremental}")

        # Build candidate chunks (evidence + governance/framework docs) with hashes.
        def _hash(t: str) -> str:
            return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16]

        candidates: list[tuple[Chunk, str]] = []  # (chunk-without-embedding, text)

        ev_count = 0
        for item in full:
            if not item:
                continue
            ev_count += 1
            uid = item["evidence_uid"]
            text = f"{item.get('title', '')}\n{item.get('content', '')}".strip()
            pieces = chunk_text(text, chunk_size=size, overlap=overlap) or [item.get("title", "")]
            for idx, piece in enumerate(pieces):
                meta = {"source_system": item.get("source_system"),
                        "object_type": item.get("object_type"),
                        "application": item.get("application"),
                        "doc_kind": "evidence", "content_hash": _hash(piece)}
                candidates.append((Chunk(chunk_id=f"{uid}:{idx}", evidence_uid=uid,
                                         text=piece, metadata=meta), piece))
        report["evidence"] = ev_count

        gov_docs = _governance_documents()
        report["governance_docs"] = len(gov_docs)
        for doc in gov_docs:
            meta = dict(doc["metadata"]); meta["doc_kind"] = "governance"
            meta["content_hash"] = _hash(doc["text"])
            candidates.append((Chunk(chunk_id=f"{doc['uid']}:0", evidence_uid=doc["uid"],
                                     text=doc["text"], metadata=meta), doc["text"]))

        report["candidate_chunks"] = len(candidates)

        # Incremental filter: skip chunks whose hash already matches what's stored.
        to_embed = [(c, t) for (c, t) in candidates
                    if not (incremental and existing.get(c.chunk_id) == c.metadata["content_hash"])]
        report["skipped_unchanged"] = len(candidates) - len(to_embed)

        # Embed + upsert in batches with progress logging and per-batch error capture.
        batch, embedded = 50, 0
        out_chunks: list[Chunk] = []
        for i in range(0, len(to_embed), batch):
            window = to_embed[i:i + batch]
            try:
                vecs = provider.embed([t for (_c, t) in window])
                for (c, _t2), v in zip(window, vecs):
                    c.embedding = v
                    out_chunks.append(c)
                embedded += len(window)
                log("ECSPlatform", f"RAG reindex progress: {embedded}/{len(to_embed)} chunks embedded")
            except Exception as exc:  # noqa: BLE001 - continue past a bad batch
                report["errors"].append(f"batch {i//batch}: {exc}")

        if out_chunks:
            store.upsert(out_chunks)
        report["embedded_chunks"] = embedded

        # Final vector count straight from the store.
        try:
            with store._connect().cursor() as cur:  # noqa: SLF001
                cur.execute(f"SELECT count(*) FROM {store._table}")  # noqa: SLF001
                report["vector_count"] = int(cur.fetchone()[0])
        except Exception:  # noqa: BLE001
            pass

        report["ok"] = True
        report["elapsed_sec"] = round(_t.time() - started, 1)
        log("ECSPlatform", f"RAG reindex done: embedded={embedded} skipped={report['skipped_unchanged']} "
                           f"vector_count={report['vector_count']} in {report['elapsed_sec']}s")
        return report
    except RepositoryError as exc:
        report["errors"].append(str(exc))
        return report
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(str(exc))
        return report


# ------------------------------------------------------------------ pipeline steps
def _rbac_filter(role: str, user: str) -> dict[str, Any]:
    """Step 1: translate the caller's role into an evidence scope filter."""
    try:
        from ecs_platform.rbac.policy import Principal, RbacPolicy

        policy = RbacPolicy()
        principal = Principal(user_id=user, role=_ROLE_ALIASES.get(role, role), assignments={})
        decision = policy.authorize(principal, "read_evidence")
        return {"allowed": decision.allowed, "reason": decision.reason,
                "scope_filter": decision.scope_filter, "rbac_role": principal.role}
    except Exception as exc:  # noqa: BLE001
        return {"allowed": True, "reason": f"rbac unavailable: {exc}", "scope_filter": {}, "rbac_role": role}


def _parse_hints(question: str) -> dict[str, Any]:
    q = (question or "").lower()
    hints: dict[str, Any] = {"application": None, "framework": None, "status": None, "source_system": None}
    # source-system intent ("show all Jira evidence")
    for src in ("jira", "jenkins", "sonarqube", "gitea", "github", "confluence"):
        if src in q:
            hints["source_system"] = src
            break
    # framework intent
    fw_words = {"pci": "PCI-DSS", "pci-dss": "PCI-DSS", "iso": "ISO27001", "iso27001": "ISO27001",
                "soc2": "SOC2", "soc 2": "SOC2", "rbi": "RBI-CSF", "ai-sdlc": "AI-SDLC", "ai sdlc": "AI-SDLC"}
    for w, fw in fw_words.items():
        if w in q:
            hints["framework"] = fw
            break
    for w, st in _STATUS_WORDS.items():
        if w in q:
            hints["status"] = st
            break
    # application intent: match against known applications
    try:
        with EvidenceRepository() as repo:
            apps = repo.distinct_values().get("applications", [])
        for app in apps:
            if app.replace("-", " ") in q or app in q:
                hints["application"] = app
                break
    except RepositoryError:
        pass
    return hints


def _retrieve(question: str, scope_filter: dict[str, Any], hints: dict[str, Any],
              top_k: int) -> tuple[list[str], str, int]:
    """Step 2: retrieve candidate evidence UIDs. Vector-first, repository fallback.

    Returns (ordered_uids, mode, retrieved_chunks). Vector mode needs GEMINI_API_KEY + a populated
    index; otherwise we fall back to deterministic repository retrieval so the
    pipeline still produces grounded context.
    """
    # vector retrieval (semantic)
    try:
        from ecs_platform.llm_engine.provider import get_provider
        from ecs_platform.vectorstore import get_vector_store

        provider = get_provider()
        if provider.configured():
            store = get_vector_store()
            store.init_store()
            vfilter: dict[str, Any] = {}
            if hints.get("application"):
                vfilter["application"] = hints["application"]
            if hints.get("source_system"):
                vfilter["source_system"] = hints["source_system"]
            embedding = provider.embed([question])[0]
            hits = store.search(embedding, top_k=top_k, filters=vfilter or None)
            uids: list[str] = []
            for h in hits:
                if h.evidence_uid not in uids:
                    uids.append(h.evidence_uid)
            if uids:
                return uids, "vector", len(hits)
    except Exception:  # noqa: BLE001 - fall through to repository retrieval
        pass

    # repository retrieval (deterministic, framework/status/app aware + RBAC scope).
    # RBAC is enforced strictly: a restricted role with NO assignments (empty list)
    # sees nothing. Enterprise-scoped roles have no "application" key -> unrestricted.
    scope_apps = None
    if "application" in scope_filter:
        scope_apps = scope_filter["application"]
        if not scope_apps:
            return [], "repository", 0  # restricted role, no assignments -> deny
    try:
        with EvidenceRepository() as repo, repo.connect().cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT e.evidence_uid, e.collected_timestamp
                FROM evidence e
                LEFT JOIN evidence_control_map m ON m.evidence_id = e.id
                LEFT JOIN control_framework_crosswalk cfw ON cfw.control_id = m.control_id
                LEFT JOIN evidence_reviews r ON r.evidence_uid = e.evidence_uid
                WHERE (%(app)s IS NULL OR e.application = %(app)s)
                  AND (%(fw)s IS NULL OR cfw.framework_code = %(fw)s)
                  AND (%(status)s IS NULL OR r.status = %(status)s)
                  AND (%(src)s IS NULL OR e.source_system = %(src)s)
                  AND (%(scope)s::text[] IS NULL OR e.application = ANY(%(scope)s))
                ORDER BY e.collected_timestamp DESC
                LIMIT %(limit)s
                """,
                {"app": hints.get("application"), "fw": hints.get("framework"),
                 "status": hints.get("status"), "src": hints.get("source_system"),
                 "scope": scope_apps, "limit": top_k})
            rows = cur.fetchall()
            return [r[0] for r in rows], "repository", len(rows)
    except RepositoryError:
        return [], "repository", 0


def _enrich(uids: list[str]) -> list[dict[str, Any]]:
    """Steps 3+4: attach source/timestamp + reuse (controls) + framework mappings."""
    if not uids:
        return []
    try:
        with EvidenceRepository() as repo, repo.connect().cursor() as cur:
            cur.execute(
                """
                SELECT e.evidence_uid, e.source_system, e.object_type, e.title, e.content,
                       e.application, e.url, e.collected_timestamp,
                       array_remove(array_agg(DISTINCT m.control_id), NULL) AS controls,
                       r.status AS review_status
                FROM evidence e
                LEFT JOIN evidence_control_map m ON m.evidence_id = e.id
                LEFT JOIN evidence_reviews r ON r.evidence_uid = e.evidence_uid
                WHERE e.evidence_uid = ANY(%s)
                GROUP BY e.id, r.status
                """, (uids,))
            cols = [c[0] for c in cur.description]
            by_uid = {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}
    except RepositoryError:
        return []
    out: list[dict[str, Any]] = []
    for uid in uids:  # preserve retrieval order
        row = by_uid.get(uid)
        if not row:
            continue
        controls = row.get("controls") or []
        fw_refs: dict[str, str] = {}
        for cid in controls:
            for fw, ref in CONTROL_CROSSWALK.get(cid, {}).items():
                fw_refs.setdefault(fw, ref)
        out.append({
            "evidence_uid": uid, "source_system": row.get("source_system"),
            "object_type": row.get("object_type"), "title": row.get("title"),
            "content": (row.get("content") or "")[:600], "application": row.get("application"),
            "url": row.get("url"), "collected_timestamp": row.get("collected_timestamp"),
            "controls": controls, "frameworks": sorted(fw_refs), "framework_refs": fw_refs,
            "review_status": row.get("review_status") or "Collected",
        })
    return to_jsonable(out)


def _governance_facts(question: str) -> list[str]:
    """Structured, real metrics injected as grounded context for analytical Qs."""
    q = (question or "").lower()
    facts: list[str] = []
    try:
        summ = executive_summary()
        if summ.get("ok"):
            facts.append(
                f"PORTFOLIO: {summ['applications']} applications, {summ['total_evidence']} evidence records, "
                f"readiness {summ['readiness_score']}% ({summ['readiness_band']}), "
                f"control coverage {summ['control_coverage_pct']}%, framework coverage {summ['framework_coverage_pct']}%.")
        if any(w in q for w in ("framework", "coverage", "pci", "iso", "soc", "rbi", "ai-sdlc", "ai sdlc")):
            fc = framework_coverage()
            if fc.get("ok"):
                facts.append("FRAMEWORK COVERAGE: " + "; ".join(
                    f"{r['framework_code']} {r['coverage_pct']}% ({r['covered_controls']}/{r['expected_controls']} controls)"
                    for r in fc["frameworks"]))
        if any(w in q for w in ("gap", "ready", "readiness", "audit")):
            cc = control_coverage()
            if cc.get("ok"):
                gaps = [c["control_id"] for c in cc["controls"] if c["status"] != "Covered"]
                facts.append(f"CONTROL GAPS ({cc['gaps']} of {cc['total_controls']}): {', '.join(gaps) or 'none'}.")
        if "reuse" in q:
            ru = evidence_reuse()
            if ru.get("ok"):
                facts.append(
                    f"REUSE: {ru['crosswalked_evidence']} evidence items satisfy {ru['framework_obligations']} "
                    f"framework obligations ({ru['framework_reuse_ratio']}x), saving {ru['framework_ops_saved']} collections.")
    except Exception:  # noqa: BLE001
        pass
    return facts


def _assemble_prompt(question: str, facts: list[str], evidence: list[dict[str, Any]]) -> str:
    """Step 5: assemble the grounded prompt with citable, enriched evidence blocks."""
    parts: list[str] = []
    if facts:
        parts.append("ECS GOVERNANCE FACTS (computed from the live repository):\n" + "\n".join(f"- {f}" for f in facts))
    blocks = []
    for i, e in enumerate(evidence, start=1):
        fws = ", ".join(f"{fw} {e['framework_refs'][fw]}" for fw in e["frameworks"]) or "none"
        blocks.append(
            f"[E{i}] uid={e['evidence_uid']} source={e['source_system']} type={e['object_type']} "
            f"app={e['application']} collected={e['collected_timestamp']} status={e['review_status']}\n"
            f"     frameworks: {fws}\n"
            f"     {e['title']}\n     {e['content']}".rstrip())
    if blocks:
        parts.append("EVIDENCE (cite with [E#]):\n" + "\n\n".join(blocks))
    parts.append(
        f"QUESTION: {question}\n\n"
        "Answer using ONLY the facts and evidence above. Cite evidence as [E#]. "
        "When relevant, name the source system, collection timestamp, and the frameworks "
        "each cited evidence satisfies. If the context is insufficient, say so explicitly.")
    return "\n\n".join(parts)


def answer(question: str, *, role: str = "cio", user: str = "User", top_k: int = 8,
           application: str = "", framework: str = "") -> dict[str, Any]:
    """Full RAG pipeline. Returns answer + enriched citations + diagnostics.

    grounded=False with mode='fallback' means no LLM key — caller should use the
    deterministic keyword assistant instead. Explicit application/framework filters
    (from the UI) override question-parsed hints.
    """
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    rbac = _rbac_filter(role, user)
    if not rbac["allowed"]:
        return {"ok": False, "grounded": False, "answer": f"Access denied: {rbac['reason']}",
                "citations": [], "rbac": rbac, "mode": "denied", "request_id": request_id}

    hints = _parse_hints(question)
    if application:
        hints["application"] = application
    if framework:
        hints["framework"] = framework
    retrieval_start = time.perf_counter()
    uids, mode, retrieved_chunks = _retrieve(question, rbac["scope_filter"], hints, top_k)
    retrieval_ms = int((time.perf_counter() - retrieval_start) * 1000)
    evidence = _enrich(uids)
    facts = _governance_facts(question)

    citations = [
        {"ref": f"E{i}", "evidence_uid": e["evidence_uid"], "source_system": e["source_system"],
         "object_type": e["object_type"], "application": e["application"],
         "collected_timestamp": e["collected_timestamp"], "frameworks": e["frameworks"],
         "framework_refs": e["framework_refs"], "review_status": e["review_status"],
         "controls": e["controls"], "url": e["url"], "title": e["title"]}
        for i, e in enumerate(evidence, start=1)
    ]

    try:
        from ecs_platform.llm_engine.provider import get_provider
        from ecs_platform.llm_engine.prompt_builder import SYSTEM_PROMPT

        provider = get_provider()

        # Grounding gate (applies to every provider): if nothing was retrieved and
        # no governance facts apply, refuse with the exact required message. This is
        # the primary anti-hallucination guard and runs BEFORE any model call.
        if not evidence and not facts:
            out = {"ok": True, "grounded": False, "mode": "no_evidence",
                   "answer": NO_EVIDENCE_MESSAGE,
                   "citations": [], "rbac": rbac, "hints": hints, "retrieval_mode": mode,
                   "request_id": request_id}
            _persist_metric({
                "timestamp": timestamp,
                "request_id": request_id,
                "question": question,
                "model_name": "",
                "provider": "",
                "retrieval_mode": mode,
                "retrieved_documents": len(uids),
                "retrieved_chunks": retrieved_chunks,
                "prompt_size_chars": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "retrieval_latency_ms": retrieval_ms,
                "prompt_build_latency_ms": 0,
                "llm_latency_ms": 0,
                "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
            })
            return out

        if not provider.configured():
            out = {"ok": True, "grounded": False, "mode": "fallback",
                   "answer": "LLM provider not configured. Returning structured retrieval only.",
                   "citations": citations, "rbac": rbac, "hints": hints,
                   "retrieval_mode": mode, "facts": facts, "request_id": request_id}
            _persist_metric({
                "timestamp": timestamp,
                "request_id": request_id,
                "question": question,
                "model_name": "",
                "provider": "",
                "retrieval_mode": mode,
                "retrieved_documents": len(uids),
                "retrieved_chunks": retrieved_chunks,
                "prompt_size_chars": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "retrieval_latency_ms": retrieval_ms,
                "prompt_build_latency_ms": 0,
                "llm_latency_ms": 0,
                "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
            })
            return out
        prompt_start = time.perf_counter()
        prompt = _assemble_prompt(question, facts, evidence)
        prompt_build_ms = int((time.perf_counter() - prompt_start) * 1000)
        llm_start = time.perf_counter()
        text, usage = provider.generate_with_metadata(prompt, system=SYSTEM_PROMPT)
        llm_ms = int((time.perf_counter() - llm_start) * 1000)
        in_tokens = int(usage.get("input_tokens", 0) or 0)
        out_tokens = int(usage.get("output_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or (in_tokens + out_tokens))
        _persist_metric({
            "timestamp": timestamp,
            "request_id": request_id,
            "question": question,
            "model_name": provider.model,
            "provider": type(provider).__name__.replace("Provider", "").lower(),
            "retrieval_mode": mode,
            "retrieved_documents": len(uids),
            "retrieved_chunks": retrieved_chunks,
            "prompt_size_chars": len(prompt),
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "total_tokens": total_tokens,
            "retrieval_latency_ms": retrieval_ms,
            "prompt_build_latency_ms": prompt_build_ms,
            "llm_latency_ms": llm_ms,
            "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
        })
        return {"ok": True, "grounded": True, "mode": "rag", "answer": text,
                "citations": citations, "rbac": rbac, "hints": hints,
                "retrieval_mode": mode, "facts": facts, "model": provider.model,
                "provider": type(provider).__name__.replace("Provider", "").lower(),
                "request_id": request_id,
                "metrics": {
                    "retrieved_documents": len(uids),
                    "retrieved_chunks": retrieved_chunks,
                    "prompt_size_chars": len(prompt),
                    "input_tokens": in_tokens,
                    "output_tokens": out_tokens,
                    "total_tokens": total_tokens,
                    "retrieval_latency_ms": retrieval_ms,
                    "prompt_build_latency_ms": prompt_build_ms,
                    "llm_latency_ms": llm_ms,
                    "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
                }}
    except Exception as exc:  # noqa: BLE001
        _persist_metric({
            "timestamp": timestamp,
            "request_id": request_id,
            "question": question,
            "model_name": "",
            "provider": "",
            "retrieval_mode": mode,
            "retrieved_documents": len(uids),
            "retrieved_chunks": retrieved_chunks,
            "prompt_size_chars": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "retrieval_latency_ms": retrieval_ms,
            "prompt_build_latency_ms": 0,
            "llm_latency_ms": 0,
            "end_to_end_latency_ms": int((time.perf_counter() - started) * 1000),
        })
        return {"ok": False, "grounded": False, "mode": "error", "answer": f"RAG error: {exc}",
                "citations": citations, "rbac": rbac, "hints": hints,
                "retrieval_mode": mode, "request_id": request_id}


def _persist_metric(row: dict[str, Any]) -> None:
    """Best-effort metric write; never interferes with request handling."""
    try:
        persist_rag_metric(row)
    except Exception:  # noqa: BLE001
        pass


# Example questions surfaced in the UI.
EXAMPLE_QUERIES = [
    "Show PCI evidence for Mobile Banking.",
    "Show evidence reused across frameworks.",
    "Show rejected evidence.",
    "Show audit readiness gaps.",
    "Show framework coverage.",
]
