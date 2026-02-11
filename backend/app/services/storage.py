from __future__ import annotations

import io
import os
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.config import settings


class StorageService:
    """Abstraction over S3 or local filesystem for file storage."""

    def __init__(self):
        self._use_s3 = bool(settings.s3_bucket and settings.aws_access_key_id)
        if self._use_s3:
            self._client = boto3.client(
                "s3",
                region_name=settings.s3_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
            )
            self._bucket = settings.s3_bucket
        else:
            self._local_root = Path(os.getenv("LOCAL_STORAGE_PATH", "/tmp/rfp-storage"))
            self._local_root.mkdir(parents=True, exist_ok=True)

    def upload(self, data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
        if self._use_s3:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
            return f"s3://{self._bucket}/{key}"

        local_path = self._local_root / key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        return str(local_path)

    def download(self, key: str) -> bytes:
        if self._use_s3:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        local_path = self._local_root / key
        return local_path.read_bytes()

    def delete(self, key: str) -> None:
        if self._use_s3:
            try:
                self._client.delete_object(Bucket=self._bucket, Key=key)
            except ClientError:
                pass
            return

        local_path = self._local_root / key
        if local_path.exists():
            local_path.unlink()

    def generate_key(self, org_id: str, filename: str) -> str:
        ext = Path(filename).suffix
        return f"knowledge/{org_id}/{uuid.uuid4().hex}{ext}"


storage_service = StorageService()
