"""Evidence capabilities: upload, retrieve, verify (hash), version, metadata, traceability.

Targets the real ECS routes:
  POST /evidence/upload            (modules/shared/routes/evidence_routes.py)  single upload, JSON when Accept: application/json
  POST /mvp/upload/bulk            (modules/shared/routes/routes_mvp.py)       bulk upload (redirect + notice)
  POST /evidence/upload (same file, new bytes) = new version; POST /workflow/upload-version logs the version audit event
  GET  /evidence/repository, GET /evidence/{id}                                 repository list / detail
  GET  /api/evidence/search, /api/evidence/repository, /api/audit/evidence      search & authoritative reader
  GET  /api/evidence/{id}/integrity, /api/evidence/{key}/quality, /api/audit/evidence/{key}/versions|timeline
  GET  /api/evidence/naming-preview, POST /api/evidence/validate-metadata
"""

from __future__ import annotations

from typing import Any, Iterable

from .api_client import ApiResponse, EcsApiClient
from .data_factory import DataFactory, TestFile

JSON = {"Accept": "application/json"}
_ID_KEYS = ("evidence_id", "display_evidence_id", "repository_id", "evidence_uid", "evidence_key", "id")


def _items(body: Any) -> list[dict]:
    if isinstance(body, list):
        return [x for x in body if isinstance(x, dict)]
    if isinstance(body, dict):
        for key in ("items", "rows", "results", "records", "evidence", "data"):
            val = body.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
            if isinstance(val, dict):
                inner = _items(val)
                if inner:
                    return inner
    return []


def evidence_id_of(row: dict) -> str:
    for k in _ID_KEYS:
        if row.get(k):
            return str(row[k])
    return ""


class EvidenceHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory) -> None:
        self.api, self.data = api, data
        self.created: list[dict[str, Any]] = []   # evidence this run created (cleanup / evidence capture)

    # ---- upload -----------------------------------------------------------------------------------------------
    def upload(self, f: TestFile | None = None, *, persona: str | None = None, **meta: Any) -> ApiResponse:
        """Single upload through ECS (POST /evidence/upload). Records the created evidence id on success."""
        f = f or self.data.file()
        client = self.api.as_persona(persona) if persona else self.api
        fields = {k: v for k, v in self.data.evidence_metadata(**meta).items() if v is not None}
        resp = client.post("/evidence/upload", data=fields, files={"evidence_file": (f.name, f.content, f.mime)}, headers=JSON)
        if resp.status == 200 and resp.is_json:
            body = resp.json()
            if isinstance(body, dict) and body.get("status") == "success":
                self.created.append({"evidence_id": body.get("evidence_id"), "repository_id": body.get("repository_id"),
                                     "filename": f.name, "sha256": f.sha256, "request_id": resp.request_id})
        return resp

    def bulk_upload(self, files: Iterable[TestFile], *, persona: str | None = None, framework: str | None = None,
                    application: str | None = None) -> ApiResponse:
        client = self.api.as_persona(persona) if persona else self.api
        payload = [("files", (f.name, f.content, f.mime)) for f in files]
        return client.post("/mvp/upload/bulk", files=payload,
                           data={"framework": framework if framework is not None else self.data.framework(),
                                 "application": application or self.data.application()})

    def upload_new_version(self, f: TestFile, *, persona: str | None = None, **meta: Any) -> ApiResponse:
        """New version = re-upload of the same filename/control with changed bytes through /evidence/upload.
        (POST /workflow/upload-version in app/main.py only logs an audit event - see stage_version_event.)"""
        return self.upload(f, persona=persona, **meta)

    def stage_version_event(self, control_name: str, framework_name: str, evidence_id: str = "") -> ApiResponse:
        """POST /workflow/upload-version: ECS records the 'Evidence Version Uploaded' audit event + notice."""
        return self.api.post("/workflow/upload-version", data={
            "control_name": control_name, "framework_name": framework_name, "evidence_id": evidence_id})

    def revalidate(self, **kw: str) -> ApiResponse:
        return self.api.post("/evidence/revalidate", data=kw, headers=JSON)

    def submit_for_review(self, evidence_id: str, **kw: str) -> ApiResponse:
        """POST /evidence/submit (framework required; control/application/evidence_id optional)."""
        return self.api.post("/evidence/submit", headers=JSON, data={
            "framework": kw.pop("framework", self.data.framework()), "application": kw.pop("application", self.data.application()),
            "evidence_id": evidence_id, **kw})

    # ---- retrieve ----------------------------------------------------------------------------------------------
    def repository(self, limit: int = 500) -> list[dict]:
        return _items(self.api.get_json("/evidence/repository", params={"limit": limit}))

    def get(self, evidence_id: str) -> ApiResponse:
        return self.api.get(f"/evidence/{evidence_id}")

    def search(self, q: str = "", **filters: str) -> list[dict]:
        """GET /api/evidence/search (q, framework, application, owner, status, limit, offset)."""
        return _items(self.api.get_json("/api/evidence/search", params={"q": q, **filters}))

    def audit_repository(self, **filters: str) -> list[dict]:
        """Audit-intelligence repository (GET /api/audit/repository: query, technology, framework, asset_id, verdict, tag)."""
        return _items(self.api.get_json("/api/audit/repository", params=filters))

    def find_all(self, **criteria: Any) -> list[dict]:
        """Rows from the repository whose fields contain every criterion (case-insensitive substring)."""
        rows = self.repository()
        out = []
        for r in rows:
            blob = {k: str(v).lower() for k, v in r.items()}
            if all(str(v).lower() in blob.get(k, "") for k, v in criteria.items()):
                out.append(r)
        return out

    def find(self, **criteria: Any) -> dict | None:
        rows = self.find_all(**criteria)
        return rows[0] if rows else None

    def by_filename(self, filename: str) -> dict | None:
        return self.find(filename=filename)

    # ---- verify / integrity -----------------------------------------------------------------------------------
    def integrity(self, evidence_id: str) -> ApiResponse:
        return self.api.get(f"/api/evidence/{evidence_id}/integrity")

    def quality(self, evidence_key: str) -> ApiResponse:
        return self.api.get(f"/api/evidence/{evidence_key}/quality")

    def stored_hash(self, evidence_id: str) -> str:
        body = self.integrity(evidence_id).json()
        return str(body.get("stored_hash") or "")

    # ---- version / timeline --------------------------------------------------------------------------------------
    def versions(self, evidence_key: str) -> list[dict]:
        body = self.api.get_json(f"/api/audit/evidence/{evidence_key}/versions")
        return body.get("versions", []) if isinstance(body, dict) else []

    def timeline(self, evidence_key: str) -> list[dict]:
        body = self.api.get_json(f"/api/audit/evidence/{evidence_key}/timeline")
        return _items(body) or (body.get("timeline", []) if isinstance(body, dict) else [])

    # ---- metadata / naming -------------------------------------------------------------------------------------
    def naming_preview(self, filename: str, framework: str | None = None, application: str | None = None) -> ApiResponse:
        return self.api.get("/api/evidence/naming-preview", params={
            "filename": filename, "framework": framework or self.data.framework(),
            "application": application or self.data.application()})

    def validate_metadata(self, payload: dict[str, Any]) -> ApiResponse:
        return self.api.post("/api/evidence/validate-metadata", json=payload)

    # ---- helpers for cleanup/evidence capture ---------------------------------------------------------------------
    def last_created(self) -> dict[str, Any]:
        assert self.created, "no evidence has been uploaded by this test yet"
        return self.created[-1]
