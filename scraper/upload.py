"""Ladda upp scraperresultat till Cloudflare R2 via S3-kompatibelt API."""

import logging
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger("fm-avlysning.upload")

# Filer som laddas upp vid varje körning
UPLOAD_FILES = [
    ("skjutfalt_status.json", "application/json"),
]


def upload_to_r2(data_dir: Path) -> None:
    """Ladda upp datafiler till R2-bucket.

    Kräver följande miljövariabler:
        S3_ENDPOINT_URL     — t.ex. https://<account-id>.r2.cloudflarestorage.com
        S3_ACCESS_KEY_ID    — R2 API-token access key
        S3_SECRET_ACCESS_KEY — R2 API-token secret key
        S3_BUCKET_NAME      — t.ex. fm-avlysning
    """
    endpoint_url = os.environ.get("S3_ENDPOINT_URL")
    access_key = os.environ.get("S3_ACCESS_KEY_ID")
    secret_key = os.environ.get("S3_SECRET_ACCESS_KEY")
    bucket_name = os.environ.get("S3_BUCKET_NAME")

    missing = []
    if not endpoint_url:
        missing.append("S3_ENDPOINT_URL")
    if not access_key:
        missing.append("S3_ACCESS_KEY_ID")
    if not secret_key:
        missing.append("S3_SECRET_ACCESS_KEY")
    if not bucket_name:
        missing.append("S3_BUCKET_NAME")

    if missing:
        raise RuntimeError(
            f"Saknade miljövariabler för R2-upload: {', '.join(missing)}"
        )

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
    )

    for filename, content_type in UPLOAD_FILES:
        filepath = data_dir / filename
        if not filepath.exists():
            logger.warning("Filen %s saknas, hoppar över upload", filepath)
            continue

        try:
            s3.upload_file(
                str(filepath),
                bucket_name,
                f"data/{filename}",
                ExtraArgs={"ContentType": content_type},
            )
            logger.info("Uppladdad: %s → s3://%s/data/%s", filepath, bucket_name, filename)
        except ClientError:
            logger.exception("Misslyckades att ladda upp %s", filename)
            raise
