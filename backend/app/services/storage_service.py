import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    _s3_client = None

    @classmethod
    def get_s3_client(cls):
        if not settings.ENABLE_S3_STORAGE:
            return None
        if cls._s3_client is None:
            try:
                import boto3
                from botocore.config import Config
                cls._s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.S3_REGION,
                    config=Config(signature_version="s3v4", s3={"addressing_style": "path"})
                )
                cls._ensure_bucket_exists()
            except Exception as e:
                logger.warning(f"Could not initialize S3 client: {e}. Falling back to local storage.")
                return None
        return cls._s3_client

    @classmethod
    def _ensure_bucket_exists(cls) -> None:
        try:
            client = cls._s3_client
            if not client:
                return
            bucket = settings.S3_BUCKET_NAME
            try:
                client.head_bucket(Bucket=bucket)
            except Exception:
                try:
                    client.create_bucket(Bucket=bucket)
                    logger.info(f"Created S3/MinIO bucket '{bucket}'.")
                except Exception as ce:
                    logger.warning(f"Bucket '{bucket}' check/creation warning: {ce}")
        except Exception as e:
            logger.warning(f"Bucket ensure error: {e}")

    @classmethod
    def upload_file(cls, local_path: Path, s3_key: str, content_type: str = "video/mp4") -> Optional[str]:
        """Upload a file to S3 if enabled. Returns S3 URL or None."""
        client = cls.get_s3_client()
        if not client:
            return None
        try:
            client.upload_file(
                str(local_path),
                settings.S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={"ContentType": content_type}
            )
            if settings.S3_PUBLIC_URL_PREFIX:
                return f"{settings.S3_PUBLIC_URL_PREFIX.rstrip('/')}/{settings.S3_BUCKET_NAME}/{s3_key}"
            elif settings.S3_ENDPOINT_URL:
                return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{s3_key}"
            return f"s3://{settings.S3_BUCKET_NAME}/{s3_key}"
        except Exception as e:
            logger.error(f"S3 upload failed for {s3_key}: {e}")
            return None

    @classmethod
    def upload_bytes(cls, data: bytes, s3_key: str, content_type: str = "application/json") -> Optional[str]:
        """Upload raw bytes to S3 if enabled. Returns S3 URL or None."""
        client = cls.get_s3_client()
        if not client:
            return None
        try:
            client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=data,
                ContentType=content_type
            )
            if settings.S3_PUBLIC_URL_PREFIX:
                return f"{settings.S3_PUBLIC_URL_PREFIX.rstrip('/')}/{settings.S3_BUCKET_NAME}/{s3_key}"
            elif settings.S3_ENDPOINT_URL:
                return f"{settings.S3_ENDPOINT_URL.rstrip('/')}/{settings.S3_BUCKET_NAME}/{s3_key}"
            return f"s3://{settings.S3_BUCKET_NAME}/{s3_key}"
        except Exception as e:
            logger.error(f"S3 upload bytes failed for {s3_key}: {e}")
            return None
