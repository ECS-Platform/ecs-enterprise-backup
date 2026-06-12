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
from ecs_platform.repository import EvidenceRepository, RepositoryError

# Exact refusal message when retrieval yields nothing (anti-hallucination contract).
NO_EVIDENCE_MESSAGE = "No evidence found in ECS repository."

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
                           "embed_dim": 0, "detail": ""}
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
        txt = provider.generate("Reply with the single word OK.", system="You are a health probe.")
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

            # lineage edges (evidence_relationships)
            cur.execute(
                """
                SELECT e.evidence_uid, l.parent_uid, l.operation, e.application
                FROM evidence_lineage l JOIN evidence e ON e.id = l.evidence_id
                """)
            for child, parent, op, app in cur.fetchall():
                docs.append({
                    "uid": f"lineage:{parent}->{child}",
                    "text": f"Evidence relationship: {parent} -> {child} via {op} (app {app}).",
                    "metadata": {"source_system": "governance", "object_type": "relationship",
                                 "application": app or ""}})

            # audit history
            cur.execute(
                "SELECT actor, role, action, resource, created_at FROM audit_log ORDER BY created_at DESC LIMIT 500")
            for actor, role, action, resource, ts in cur.fetchall():
                docs.append({
                    "uid": f"audit:{action}:{resource}:{ts}",
                    "text": f"Audit event at {ts}: {actor} ({role}) performed {action} on {resource}.",
                    "metadata": {"source_system": "governance", "object_type": "audit", "application": ""}})
    except (RepositoryError, Exception):  # noqa: BLE001 - governance tables optional
        pass
    return docs


def reindex_evidence(limit: int = 5000) -> dict[str, Any]:
    """Embed all repository evidence + governance docs into pgvector (needs GEMINI_API_KEY).

    Indexes: evidence, evidence_relationships, governance observations, application
    inventory, framework mappings, audit history. Idempotent — pgvector upserts on
    chunk_id, so re-running only refreshes. No new evidence is created."""
    try:
        from ecs_platform.config import load_vectorstore_config
        from ecs_platform.llm_engine.provider import get_provider
        from ecs_platform.vectorstore import Chunk, chunk_text, get_vector_store

        provider = get_provider()
        if not provider.configured():
            return {"ok": False, "error": "GEMINI_API_KEY not set; cannot embed."}

        chunk_cfg = (load_vectorstore_config().get("vectorstore", {}) or {}).get("chunking", {})
        size = int(chunk_cfg.get("chunk_size", 1000))
        overlap = int(chunk_cfg.get("chunk_overlap", 150))

        with EvidenceRepository() as repo:
            rows = repo.search_evidence(limit=limit)
            full = [repo.evidence_by_uid(r["evidence_uid"]) for r in rows]

        store = get_vector_store()
        store.init_store()

        chunks: list[Chunk] = []
        # 1. evidence records
        ev_count = 0
        for item in full:
            if not item:
                continue
            ev_count += 1
            uid = item["evidence_uid"]
            text = f"{item.get('title', '')}\n{item.get('content', '')}".strip()
            pieces = chunk_text(text, chunk_size=size, overlap=overlap) or [item.get("title", "")]
            embeddings = provider.embed(pieces)
            meta = {"source_system": item.get("source_system"),
                    "object_type": item.get("object_type"),
                    "application": item.get("application"),
                    "doc_kind": "evidence"}
            for idx, (piece, emb) in enumerate(zip(pieces, embeddings)):
                chunks.append(Chunk(chunk_id=f"{uid}:{idx}", evidence_uid=uid, text=piece,
                                    embedding=emb, metadata=meta))

        # 2. governance / relationships / inventory / frameworks / audit documents
        gov_docs = _governance_documents()
        for doc in gov_docs:
            emb = provider.embed([doc["text"]])[0]
            meta = dict(doc["metadata"]); meta["doc_kind"] = "governance"
            chunks.append(Chunk(chunk_id=f"{doc['uid']}:0", evidence_uid=doc["uid"],
                                text=doc["text"], embedding=emb, metadata=meta))

        indexed = store.upsert(chunks) if chunks else 0
        return {"ok": True, "evidence": ev_count, "governance_docs": len(gov_docs),
                "chunks_indexed": indexed}
    except RepositoryError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


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
              top_k: int) -> tuple[list[str], str]:
    """Step 2: retrieve candidate evidence UIDs. Vector-first, repository fallback.

    Returns (ordered_uids, mode). Vector mode needs GEMINI_API_KEY + a populated
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
                return uids, "vector"
    except Exception:  # noqa: BLE001 - fall through to repository retrieval
        pass

    # repository retrieval (deterministic, framework/status/app aware + RBAC scope).
    # RBAC is enforced strictly: a restricted role with NO assignments (empty list)
    # sees nothing. Enterprise-scoped roles have no "application" key -> unrestricted.
    scope_apps = None
    if "application" in scope_filter:
        scope_apps = scope_filter["application"]
        if not scope_apps:
            return [], "repository"  # restricted role, no assignments -> deny
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
            return [r[0] for r in cur.fetchall()], "repository"
    except RepositoryError:
        return [], "repository"


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
    rbac = _rbac_filter(role, user)
    if not rbac["allowed"]:
        return {"ok": False, "grounded": False, "answer": f"Access denied: {rbac['reason']}",
                "citations": [], "rbac": rbac, "mode": "denied"}

    hints = _parse_hints(question)
    if application:
        hints["application"] = application
    if framework:
        hints["framework"] = framework
    uids, mode = _retrieve(question, rbac["scope_filter"], hints, top_k)
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

        # Grounding gate (applies to every provider): if nothing was retrieved and
        # no governance facts apply, refuse with the exact required message. This is
        # the primary anti-hallucination guard and runs BEFORE any model call.
        if not evidence and not facts:
            return {"ok": True, "grounded": False, "mode": "no_evidence",
                    "answer": NO_EVIDENCE_MESSAGE,
                    "citations": [], "rbac": rbac, "hints": hints, "retrieval_mode": mode}

        provider = get_provider()
        if not provider.configured():
            return {"ok": True, "grounded": False, "mode": "fallback",
                    "answer": "LLM provider not configured. Returning structured retrieval only.",
                    "citations": citations, "rbac": rbac, "hints": hints,
                    "retrieval_mode": mode, "facts": facts}
        prompt = _assemble_prompt(question, facts, evidence)
        text = provider.generate(prompt, system=SYSTEM_PROMPT)
        return {"ok": True, "grounded": True, "mode": "rag", "answer": text,
                "citations": citations, "rbac": rbac, "hints": hints,
                "retrieval_mode": mode, "facts": facts, "model": provider.model,
                "provider": type(provider).__name__.replace("Provider", "").lower()}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "grounded": False, "mode": "error", "answer": f"RAG error: {exc}",
                "citations": citations, "rbac": rbac, "hints": hints, "retrieval_mode": mode}


# Example questions surfaced in the UI.
EXAMPLE_QUERIES = [
    "Show PCI evidence for Mobile Banking.",
    "Show evidence reused across frameworks.",
    "Show rejected evidence.",
    "Show audit readiness gaps.",
    "Show framework coverage.",
]
