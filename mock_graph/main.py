"""Mock Microsoft Graph API for SharePoint evidence-folder traversal (local/demo).

Serves Graph-compatible driveItem JSON from ``data/mock-sharepoint/`` fixtures.
Only implements endpoints required by ``SharePointGraphClient`` traversal.
"""

from __future__ import annotations

import hashlib
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI(title="mock-graph", version="1.0.0")

_REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "data" / "mock-sharepoint"
DRIVE_ID = "test-drive"
SITE_ID = "test-site"
MODIFIED = "2026-07-20T10:00:00Z"

# rel_path (posix, no leading slash) -> Graph item metadata
_ITEMS: dict[str, dict] = {}
# item_id -> rel_path
_ID_TO_PATH: dict[str, str] = {}


def _item_id(rel_path: str) -> str:
    digest = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:16]
    return f"item-{digest}"


def _mime(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _index_fixtures(root: Path) -> None:
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if not rel:
            continue
        iid = _item_id(rel)
        _ID_TO_PATH[iid] = rel
        if path.is_dir():
            child_count = sum(1 for c in path.iterdir())
            _ITEMS[rel] = {
                "id": iid,
                "name": path.name,
                "folder": {"childCount": child_count},
                "lastModifiedDateTime": MODIFIED,
            }
        else:
            _ITEMS[rel] = {
                "id": iid,
                "name": path.name,
                "size": path.stat().st_size,
                "webUrl": f"http://mock-graph:8080/fixtures/{rel}",
                "lastModifiedDateTime": MODIFIED,
                "file": {"mimeType": _mime(path)},
            }


_index_fixtures(FIXTURE_ROOT)


def _children(rel_prefix: str = "") -> list[dict]:
    prefix = rel_prefix.strip("/")
    out: list[dict] = []
    seen: set[str] = set()
    for rel in _ITEMS:
        if prefix:
            if rel == prefix:
                continue
            if not rel.startswith(prefix + "/"):
                continue
            remainder = rel[len(prefix) + 1 :]
        else:
            remainder = rel
        if not remainder:
            continue
        child_name = remainder.split("/")[0]
        child_rel = f"{prefix}/{child_name}".strip("/") if prefix else child_name
        if child_rel in seen:
            continue
        seen.add(child_rel)
        if child_rel in _ITEMS:
            out.append(dict(_ITEMS[child_rel]))
    return out


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "mock-graph",
        "fixtures": len([p for p in _ITEMS.values() if "file" in p]),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/{tenant_id}/oauth2/v2.0/token")
@app.post("/oauth2/v2.0/token")
def token_endpoint(tenant_id: str = ""):
    return {"access_token": "mock-graph-token", "token_type": "Bearer", "expires_in": 3600}


@app.get("/v1.0/sites/{site_id}/drives")
def site_drives(site_id: str):
    return {
        "value": [{
            "id": DRIVE_ID,
            "name": "Evidence Library",
            "driveType": "documentLibrary",
            "webUrl": f"http://mock-graph:8080/sites/{site_id}",
            "lastModifiedDateTime": MODIFIED,
        }]
    }


@app.get("/v1.0/drives/{drive_id}/root/children")
def root_children(drive_id: str):
    if drive_id != DRIVE_ID:
        raise HTTPException(status_code=404, detail="drive not found")
    return {"value": _children("")}


@app.get("/v1.0/drives/{drive_id}/root:/{folder_path:path}:/children")
def folder_path_children(drive_id: str, folder_path: str):
    if drive_id != DRIVE_ID:
        raise HTTPException(status_code=404, detail="drive not found")
    return {"value": _children(folder_path.strip("/"))}


@app.get("/v1.0/drives/{drive_id}/items/{item_id}/children")
def item_children(drive_id: str, item_id: str):
    if drive_id != DRIVE_ID:
        raise HTTPException(status_code=404, detail="drive not found")
    rel = _ID_TO_PATH.get(item_id, "")
    if not rel or "folder" not in _ITEMS.get(rel, {}):
        return {"value": []}
    return {"value": _children(rel)}


@app.get("/v1.0/drives/{drive_id}/items/{item_id}/content")
def file_content(drive_id: str, item_id: str):
    if drive_id != DRIVE_ID:
        raise HTTPException(status_code=404, detail="drive not found")
    rel = _ID_TO_PATH.get(item_id, "")
    if not rel:
        raise HTTPException(status_code=404, detail="item not found")
    path = FIXTURE_ROOT / rel
    if not path.is_file():
        raise HTTPException(status_code=404, detail="not a file")
    return FileResponse(path, media_type=_mime(path))


@app.get("/fixtures/{file_path:path}")
def fixture_view(file_path: str):
    path = FIXTURE_ROOT / file_path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="fixture not found")
    return FileResponse(path, media_type=_mime(path))
