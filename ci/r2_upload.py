"""Cloudflare R2 artifact upload with credentials from GCP Secrets Manager."""

import mimetypes
from typing import Any
from pathlib import Path

import boto3  # type: ignore[import-untyped]
from google.cloud import secretmanager  # type: ignore[import-untyped]

# GCP Secret Manager secret names for R2 credentials
_R2_ACCESS_KEY_SECRET = "r2-access-key-id"
_R2_SECRET_KEY_SECRET = "r2-secret-access-key"
_R2_ENDPOINT_SECRET = "r2-endpoint-url"
_R2_BUCKET_SECRET = "r2-bucket-name"


def _fetch_secret(client: Any, project_id: str, secret_id: str) -> str:
    """Fetch the latest version of a secret from GCP Secrets Manager.

    Args:
        client: Secret Manager client.
        project_id: GCP project ID.
        secret_id: Name of the secret to retrieve.

    Returns:
        The secret value as a string.

    Raises:
        google.api_core.exceptions.NotFound: If the secret does not exist.
    """
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


def get_r2_credentials(gcp_project_id: str) -> dict[str, str]:
    """Retrieve all Cloudflare R2 credentials from GCP Secrets Manager.

    Args:
        gcp_project_id: GCP project ID containing the secrets.

    Returns:
        Dictionary with keys: access_key_id, secret_access_key,
        endpoint_url, bucket_name.
    """
    client: Any = secretmanager.SecretManagerServiceClient()  # pyright: ignore

    return {
        "access_key_id": _fetch_secret(client, gcp_project_id, _R2_ACCESS_KEY_SECRET),
        "secret_access_key": _fetch_secret(
            client, gcp_project_id, _R2_SECRET_KEY_SECRET
        ),
        "endpoint_url": _fetch_secret(client, gcp_project_id, _R2_ENDPOINT_SECRET),
        "bucket_name": _fetch_secret(client, gcp_project_id, _R2_BUCKET_SECRET),
    }


def upload_to_r2(
    release_dir: Path,
    gcp_project_id: str,
    run_id: str,
) -> list[str]:
    """Upload release artifacts to Cloudflare R2.

    Fetches R2 credentials from GCP Secrets Manager, then uploads all
    files in the release directory to the R2 bucket under a builds/<run_id>/
    prefix.

    Args:
        release_dir: Directory containing release files to upload.
        gcp_project_id: GCP project ID for Secrets Manager lookups.
        run_id: Unique identifier for this build run.

    Returns:
        List of uploaded R2 object keys.

    Raises:
        FileNotFoundError: If release_dir does not exist.
        botocore.exceptions.ClientError: If R2 upload fails.
    """
    if not release_dir.is_dir():
        raise FileNotFoundError(f"Release directory not found: {release_dir}")

    credentials = get_r2_credentials(gcp_project_id)

    s3_client: Any = boto3.client(  # pyright: ignore
        "s3",
        endpoint_url=credentials["endpoint_url"],
        aws_access_key_id=credentials["access_key_id"],
        aws_secret_access_key=credentials["secret_access_key"],
    )

    bucket = credentials["bucket_name"]
    prefix = f"builds/{run_id}"
    uploaded_keys: list[str] = []

    for file_path in sorted(release_dir.iterdir()):
        if not file_path.is_file():
            continue

        key = f"{prefix}/{file_path.name}"
        content_type, _ = mimetypes.guess_type(str(file_path))

        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type

        print(f"  Uploading {file_path.name} → {key}")
        s3_client.upload_file(  # pyright: ignore[reportUnknownMemberType]
            str(file_path),
            bucket,
            key,
            ExtraArgs=extra_args,
        )
        uploaded_keys.append(key)

    print(
        f"Uploaded {len(uploaded_keys)} files to R2 bucket '{bucket}' under '{prefix}/'"
    )
    return uploaded_keys
