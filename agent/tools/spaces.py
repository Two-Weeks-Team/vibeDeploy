import io
import logging
import os
import tarfile

logger = logging.getLogger(__name__)


class SpacesClient:
    """DigitalOcean Spaces client (S3-compatible) for artifact storage."""

    def __init__(
        self,
        bucket_name: str | None = None,
        endpoint: str | None = None,
    ) -> None:
        self.bucket_name = bucket_name or os.getenv("DO_SPACES_BUCKET", "vibedeploy-artifacts")
        region = os.getenv("DO_SPACES_REGION", "nyc3")
        self.endpoint = endpoint or f"https://{region}.digitaloceanspaces.com"

        key = os.getenv("DO_SPACES_KEY")
        secret = os.getenv("DO_SPACES_SECRET")

        if not key or not secret:
            logger.warning("DO_SPACES_KEY or DO_SPACES_SECRET not set; Spaces operations will be no-ops")
            self._client = None
            return

        try:
            import boto3

            self._client = boto3.client(
                "s3",
                region_name=region,
                endpoint_url=self.endpoint,
                aws_access_key_id=key,
                aws_secret_access_key=secret,
            )
        except Exception as exc:
            logger.warning("Failed to initialise boto3 Spaces client: %s", exc)
            self._client = None

    def upload_archive(self, app_name: str, source_code: dict[str, str]) -> str:
        """Create a .tar.gz archive from *source_code* and upload it to Spaces.

        Returns the public URL of the uploaded object, or an empty string on failure.
        """
        if self._client is None:
            return ""

        try:
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w:gz") as tar:
                for path, content in source_code.items():
                    encoded = content.encode("utf-8")
                    info = tarfile.TarInfo(name=path)
                    info.size = len(encoded)
                    tar.addfile(info, io.BytesIO(encoded))

            buf.seek(0)
            key = f"{app_name}/{app_name}.tar.gz"
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=buf.read(),
                ContentType="application/gzip",
                ACL="public-read",
            )
            return self.get_download_url(key)
        except Exception as exc:
            logger.warning("upload_archive failed: %s", exc)
            return ""

    def upload_file(self, key: str, data: bytes, content_type: str) -> str:
        """Upload arbitrary *data* under *key*.

        Returns the public URL, or an empty string on failure.
        """
        if self._client is None:
            return ""

        try:
            self._client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType=content_type,
                ACL="public-read",
            )
            return self.get_download_url(key)
        except Exception as exc:
            logger.warning("upload_file failed for key=%s: %s", key, exc)
            return ""

    def get_download_url(self, key: str) -> str:
        """Return the public CDN/endpoint URL for *key*."""
        return f"{self.endpoint}/{self.bucket_name}/{key}"

    def list_artifacts(self, prefix: str) -> list[dict]:
        """List all objects whose key starts with *prefix*.

        Returns a list of dicts with keys: ``key``, ``size``, ``last_modified``, ``url``.
        On failure (including missing credentials) returns an empty list.
        """
        if self._client is None:
            return []

        try:
            response = self._client.list_objects_v2(Bucket=self.bucket_name, Prefix=prefix)
            results = []
            for obj in response.get("Contents", []):
                k = obj.get("Key", "")
                results.append(
                    {
                        "key": k,
                        "size": obj.get("Size", 0),
                        "last_modified": str(obj.get("LastModified", "")),
                        "url": self.get_download_url(k),
                    }
                )
            return results
        except Exception as exc:
            logger.warning("list_artifacts failed for prefix=%s: %s", prefix, exc)
            return []
