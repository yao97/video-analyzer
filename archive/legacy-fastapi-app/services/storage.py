"""
MinIO object storage service.
Manages video file upload, download, and lifecycle.
Resolves Bug #9 (hardcoded paths) and Bug #10 (temp file cleanup) by using
managed object storage with lifecycle policies.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.core.logging import get_logger

log = get_logger("storage")

# Allowed video MIME types
ALLOWED_VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
}


class StorageService:
    """MinIO-based object storage for video files and analysis results."""

    def __init__(self, client: Minio | None = None) -> None:
        self._client = client
        self._bucket = get_settings().minio_bucket

    @property
    def client(self) -> Minio:
        if self._client is None:
            from app.core.deps import get_minio
            self._client = get_minio()
        return self._client

    def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self._bucket):
                self.client.make_bucket(self._bucket)
                log.info("bucket_created", bucket=self._bucket)
        except S3Error as e:
            log.error("bucket_creation_failed", error=str(e))
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        filename: str,
        content_type: str,
        size: int | None = None,
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_data: File-like object to upload.
            filename: Original filename.
            content_type: MIME type.
            size: File size in bytes (required by MinIO).

        Returns:
            Storage key (object path in MinIO).
        """
        self.ensure_bucket()

        # Generate unique storage key
        ext = Path(filename).suffix
        storage_key = f"uploads/{uuid.uuid4()}/{filename}"

        try:
            self.client.put_object(
                bucket_name=self._bucket,
                object_name=storage_key,
                data=file_data,
                length=size if size else -1,
                content_type=content_type,
            )
            log.info(
                "file_uploaded",
                storage_key=storage_key,
                filename=filename,
                size=size,
            )
            return storage_key
        except S3Error as e:
            log.error("upload_failed", error=str(e), filename=filename)
            raise

    def upload_bytes(
        self,
        data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload raw bytes to MinIO."""
        self.ensure_bucket()
        ext = Path(filename).suffix
        storage_key = f"uploads/{uuid.uuid4()}/{filename}"

        try:
            self.client.put_object(
                bucket_name=self._bucket,
                object_name=storage_key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return storage_key
        except S3Error as e:
            log.error("upload_bytes_failed", error=str(e))
            raise

    def download_file(self, storage_key: str) -> bytes:
        """Download a file from MinIO as bytes."""
        try:
            response = self.client.get_object(self._bucket, storage_key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            log.error("download_failed", error=str(e), key=storage_key)
            raise

    def get_presigned_url(self, storage_key: str, expires: int = 3600) -> str:
        """Generate a presigned download URL for a file."""
        from datetime import timedelta
        try:
            url = self.client.presigned_get_object(
                self._bucket,
                storage_key,
                expires=timedelta(seconds=expires),
            )
            return url
        except S3Error as e:
            log.error("presign_failed", error=str(e), key=storage_key)
            raise

    def delete_file(self, storage_key: str) -> bool:
        """Delete a file from MinIO."""
        try:
            self.client.remove_object(self._bucket, storage_key)
            log.info("file_deleted", key=storage_key)
            return True
        except S3Error as e:
            log.error("delete_failed", error=str(e), key=storage_key)
            return False

    def list_files(self, prefix: str = "uploads/") -> list[dict]:
        """List files in a given prefix."""
        try:
            objects = self.client.list_objects(self._bucket, prefix=prefix, recursive=True)
            return [
                {
                    "key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                }
                for obj in objects
            ]
        except S3Error as e:
            log.error("list_failed", error=str(e))
            return []

    def cleanup_old_files(self, max_age_hours: int = 1) -> int:
        """
        Clean up files older than the specified age.
        Called by Celery beat for periodic cleanup (Bug #10 fix).
        """
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        deleted = 0

        try:
            objects = self.client.list_objects(self._bucket, prefix="uploads/", recursive=True)
            for obj in objects:
                if obj.last_modified and obj.last_modified < cutoff:
                    self.client.remove_object(self._bucket, obj.object_name)
                    deleted += 1
                    log.info("cleaned_file", key=obj.object_name, age_hours=(
                        datetime.now(timezone.utc) - obj.last_modified
                    ).total_seconds() / 3600)
        except S3Error as e:
            log.error("cleanup_failed", error=str(e))

        log.info("cleanup_complete", deleted_count=deleted)
        return deleted
