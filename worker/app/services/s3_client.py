"""S3 helpers for raw market batch persistence."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import boto3
from botocore.config import Config


class S3RawClient:
    """Simple async wrapper around boto3 for JSONL batch storage."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        prefix: str,
        endpoint_url: str | None = None,
    ) -> None:
        self.bucket = bucket
        self.region = region
        self.prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    def _normalized_key(self, key_suffix: str) -> str:
        suffix = key_suffix.lstrip("/")
        if self.prefix:
            return f"{self.prefix}/{suffix}"
        return suffix

    async def put_jsonl_batch(
        self,
        *,
        key_suffix: str,
        rows: list[dict[str, Any]],
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Store a JSONL batch in S3 and return the object key."""

        key = self._normalized_key(key_suffix)
        payload = "\n".join(
            json.dumps(row, ensure_ascii=False, default=str) for row in rows
        )

        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=payload.encode("utf-8"),
            ContentType="application/x-ndjson",
            Metadata=metadata or {},
        )
        return key

    async def get_jsonl_batch(self, *, key: str) -> list[dict[str, Any]]:
        """Load and decode a JSONL S3 object into a list of dictionaries."""

        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        raw = await asyncio.to_thread(response["Body"].read)
        text = raw.decode("utf-8")
        if not text.strip():
            return []

        rows: list[dict[str, Any]] = []
        invalid_count = 0
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                invalid_count += 1
                continue
            if isinstance(value, dict):
                rows.append(value)

        if not rows and invalid_count:
            raise ValueError(
                f"Failed to decode JSONL object {key}: no valid rows (invalid_rows={invalid_count})"
            )
        return rows
