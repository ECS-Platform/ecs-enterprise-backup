from fastapi import FastAPI

app = FastAPI(title="Local Microsoft Graph POC")

DRIVE_ID = "test-drive"

TREE = {
    "root": [
        {"id": "ecs-root", "name": "ECS-Evidence", "folder": {"childCount": 1}},
    ],
    "ecs-root": [
        {"id": "app-1", "name": "Net-Banking", "folder": {"childCount": 1}},
    ],
    "app-1": [
        {"id": "env-1", "name": "Production", "folder": {"childCount": 1}},
    ],
    "env-1": [
        {"id": "fw-1", "name": "ISO27001", "folder": {"childCount": 1}},
    ],
    "fw-1": [
        {"id": "control-1", "name": "A.8.24", "folder": {"childCount": 1}},
    ],
    "control-1": [
        {
            "id": "file-1",
            "name": "encryption_evidence.txt",
            "size": 146,
            "webUrl": "http://127.0.0.1:9100/sharepoint/encryption_evidence.txt",
            "lastModifiedDateTime": "2026-07-20T10:00:00Z",
            "file": {"mimeType": "text/plain"},
        },
    ],
}


@app.get("/health")
def health():
    return {"status": "ok", "service": "local-graph-poc"}


@app.get("/v1.0/drives/{drive_id}/root/children")
def root_children(drive_id: str):
    return {"value": TREE["root"]}


@app.get("/v1.0/drives/{drive_id}/root:/{folder_path:path}:/children")
def folder_path_children(drive_id: str, folder_path: str):
    if folder_path.strip("/") == "ECS-Evidence":
        return {"value": TREE["ecs-root"]}
    return {"value": []}

@app.get("/sharepoint/encryption_evidence.txt")
def view_evidence_file():
    return FileResponse(EVIDENCE_FILE, media_type="text/plain")

@app.get("/v1.0/drives/{drive_id}/items/{item_id}/children")
def item_children(drive_id: str, item_id: str):
    return {"value": TREE.get(item_id, [])}

from fastapi.responses import FileResponse
from pathlib import Path

EVIDENCE_FILE = Path(__file__).parent / "sharepoint_files" / "ECS-Evidence" / "Net-Banking" / "Production" / "ISO27001" / "A.8.24" / "encryption_evidence.txt"


@app.get("/v1.0/drives/{drive_id}/items/{item_id}/content")
def file_content(drive_id: str, item_id: str):
    if drive_id != "test-drive" or item_id != "file-1":
        return {"error": "file not found"}
    return FileResponse(EVIDENCE_FILE, media_type="text/plain")
