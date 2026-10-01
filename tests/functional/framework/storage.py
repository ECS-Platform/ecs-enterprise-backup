"""Object-storage / evidence-repository helper over the REAL ECS object store.

ECS stores immutable evidence bytes through ``ecs_platform.storage.object_store`` (MinIO/S3 via boto3, or the
``LocalObjectStore`` filesystem fallback). Key layout is produced by ``object_key_for_evidence`` - reused here, not
re-implemented. This helper only READS (exists / download / hash / metadata / version listing). Uploads happen
through ECS's own upload API (EvidenceHelper.upload) so no parallel storage path exists. ``tamper`` is the one write
and is guarded by the ``destructive_tests`` flag.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .config import FunctionalConfig, REPO_ROOT
from .errors import CapabilityBlocked


def object_key_for(**kw: Any) -> str:
    """Reuse ECS's key builder (source_connector, evidence_key, version, content_hash, filename)."""
    from ecs_platform.storage.object_store import object_key_for_evidence

    return object_key_for_evidence(**kw)


class ObjectStoreHelper:
    def __init__(self, cfg: FunctionalConfig) -> None:
        self.cfg = cfg
        self._s3: Any = None

    @property
    def mode(self) -> str:
        return str(self.cfg.get("object_store.mode", "local")).lower()

    # ---- backends -------------------------------------------------------------------------------------
    def _local_root(self) -> Path:
        root = Path(str(self.cfg.get("object_store.local_root", "./data/evidence-objects")))
        return root if root.is_absolute() else (REPO_ROOT / root)

    def _client(self):
        if self._s3 is None:
            os_cfg = self.cfg.get("object_store", {})
            ak = self.cfg.secret(os_cfg.get("access_key_env", "MINIO_ACCESS_KEY"))
            sk = self.cfg.secret(os_cfg.get("secret_key_env", "MINIO_SECRET_KEY"))
            if not (ak and sk):
                raise CapabilityBlocked("MinIO credentials not provided via MINIO_ACCESS_KEY / MINIO_SECRET_KEY.",
                                        requires="object store credentials")
            import boto3

            scheme = "https" if os_cfg.get("secure") else "http"
            self._s3 = boto3.client("s3", endpoint_url=f"{scheme}://{os_cfg.get('endpoint')}",
                                    aws_access_key_id=ak, aws_secret_access_key=sk)
        return self._s3

    @property
    def _bucket(self) -> str:
        return str(self.cfg.get("object_store.bucket", "ecs-evidence"))

    # ---- operations --------------------------------------------------------------------------------------
    def exists(self, key: str) -> bool:
        if self.mode == "local":
            return (self._local_root() / key).is_file()
        try:
            self._client().head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001 - botocore ClientError 404
            return False

    def download(self, key: str) -> bytes | None:
        if self.mode == "local":
            p = self._local_root() / key
            return p.read_bytes() if p.is_file() else None
        try:
            return self._client().get_object(Bucket=self._bucket, Key=key)["Body"].read()
        except Exception:  # noqa: BLE001
            return None

    def sha256(self, key: str) -> str:
        data = self.download(key)
        assert data is not None, f"object '{key}' not found in {self.mode} object store"
        return hashlib.sha256(data).hexdigest()

    def metadata(self, key: str) -> dict[str, Any]:
        if self.mode == "local":
            p = self._local_root() / key
            assert p.is_file(), f"object '{key}' not found"
            st = p.stat()
            return {"key": key, "size": st.st_size, "last_modified": st.st_mtime, "uri": p.resolve().as_uri()}
        head = self._client().head_object(Bucket=self._bucket, Key=key)
        return {"key": key, "size": head.get("ContentLength"), "last_modified": head.get("LastModified"),
                "content_type": head.get("ContentType"), "etag": head.get("ETag"), "metadata": head.get("Metadata", {})}

    def list_versions(self, evidence_key_prefix: str) -> list[str]:
        """Object keys under ``evidence/<connector>/<evidence_key>/`` -> one ``v<N>/`` folder per version (object_key_for_evidence)."""
        if self.mode == "local":
            base = self._local_root() / evidence_key_prefix
            return sorted(str(p.relative_to(self._local_root())).replace("\\", "/") for p in base.rglob("*") if p.is_file())
        resp = self._client().list_objects_v2(Bucket=self._bucket, Prefix=evidence_key_prefix)
        return sorted(o["Key"] for o in resp.get("Contents", []))

    def verify_matches(self, key: str, expected_sha256: str) -> str:
        from .assertions import assert_hash

        data = self.download(key)
        assert data is not None, f"object '{key}' missing from object store"
        return assert_hash(data, expected_sha256, f"object {key}")

    def tamper(self, key: str, suffix: bytes = b"\n#tampered-by-functional-test") -> None:
        """DESTRUCTIVE: append bytes to a TEST-CREATED object (local store only) to exercise tamper detection (UC05-FT005).
        Refused unless features.destructive_tests is enabled, and never on keys that do not carry the run prefix."""
        if not self.cfg.feature("destructive_tests"):
            raise CapabilityBlocked("Tamper simulation is destructive; set ECS_FT_ALLOW_DESTRUCTIVE=true on a disposable environment.",
                                    requires="destructive_tests flag")
        if self.mode != "local":
            raise CapabilityBlocked("Tamper simulation is only supported against the local object store (ECS S3 store is immutable).",
                                    requires="local object store")
        prefix = str(self.cfg.test_data.get("run_prefix", "FT")).lower()
        if prefix not in key.lower():
            raise CapabilityBlocked(f"Refusing to modify object '{key}': it was not created by this suite (missing '{prefix}').")
        with open(self._local_root() / key, "ab") as fh:
            fh.write(suffix)
