import io
import tarfile
from datetime import datetime
from unittest.mock import MagicMock, patch

from agent.tools.spaces import SpacesClient


def _make_client(bucket: str = "test-bucket", endpoint: str = "https://nyc3.digitaloceanspaces.com") -> SpacesClient:
    with patch.dict(
        "os.environ",
        {
            "DO_SPACES_KEY": "test-key",
            "DO_SPACES_SECRET": "test-secret",
            "DO_SPACES_BUCKET": bucket,
            "DO_SPACES_REGION": "nyc3",
        },
    ):
        with patch("boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            client = SpacesClient(bucket_name=bucket, endpoint=endpoint)
            client._boto_mock = mock_boto.return_value
            client._client = mock_boto.return_value
            return client


class TestSpacesClientInit:
    def test_missing_credentials_sets_client_none(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        client = SpacesClient()
        assert client._client is None

    def test_missing_key_only_sets_client_none(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.setenv("DO_SPACES_SECRET", "secret")
        client = SpacesClient()
        assert client._client is None

    def test_default_bucket_name(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        monkeypatch.delenv("DO_SPACES_BUCKET", raising=False)
        client = SpacesClient()
        assert client.bucket_name == "vibedeploy-artifacts"

    def test_custom_bucket_name(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        client = SpacesClient(bucket_name="my-bucket")
        assert client.bucket_name == "my-bucket"

    def test_endpoint_defaults_to_region(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        monkeypatch.setenv("DO_SPACES_REGION", "sfo3")
        client = SpacesClient()
        assert "sfo3.digitaloceanspaces.com" in client.endpoint


class TestGetDownloadUrl:
    def test_url_format(self):
        client = _make_client(bucket="my-bucket", endpoint="https://nyc3.digitaloceanspaces.com")
        url = client.get_download_url("myapp/myapp.tar.gz")
        assert url == "https://nyc3.digitaloceanspaces.com/my-bucket/myapp/myapp.tar.gz"

    def test_url_with_nested_key(self):
        client = _make_client(bucket="artifacts", endpoint="https://nyc3.digitaloceanspaces.com")
        url = client.get_download_url("apps/v1/code.tar.gz")
        assert url == "https://nyc3.digitaloceanspaces.com/artifacts/apps/v1/code.tar.gz"


class TestUploadFile:
    def test_upload_file_calls_put_object(self):
        client = _make_client()
        client._client.put_object.return_value = {}
        url = client.upload_file("test/file.json", b'{"key": "value"}', "application/json")
        client._client.put_object.assert_called_once()
        call_kwargs = client._client.put_object.call_args.kwargs
        assert call_kwargs["Key"] == "test/file.json"
        assert call_kwargs["ContentType"] == "application/json"
        assert call_kwargs["Body"] == b'{"key": "value"}'
        assert "test/file.json" in url

    def test_upload_file_missing_credentials_returns_empty(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        client = SpacesClient()
        result = client.upload_file("key", b"data", "text/plain")
        assert result == ""

    def test_upload_file_boto_exception_returns_empty(self):
        client = _make_client()
        client._client.put_object.side_effect = Exception("S3 error")
        result = client.upload_file("key", b"data", "text/plain")
        assert result == ""


class TestUploadArchive:
    def test_upload_archive_creates_tar_and_calls_put_object(self):
        client = _make_client()
        client._client.put_object.return_value = {}
        source = {"main.py": "print('hello')", "requirements.txt": "fastapi"}
        url = client.upload_archive("myapp", source)
        client._client.put_object.assert_called_once()
        call_kwargs = client._client.put_object.call_args.kwargs
        assert call_kwargs["Key"] == "myapp/myapp.tar.gz"
        assert call_kwargs["ContentType"] == "application/gzip"
        assert "myapp/myapp.tar.gz" in url

    def test_upload_archive_tar_contains_all_files(self):
        received_body: list[bytes] = []
        client = _make_client()

        def capture_put(**kwargs):
            received_body.append(kwargs["Body"])
            return {}

        client._client.put_object.side_effect = capture_put
        source = {"app/main.py": "x = 1", "app/helper.py": "y = 2"}
        client.upload_archive("proj", source)

        assert received_body, "put_object was never called"
        buf = io.BytesIO(received_body[0])
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            names = tar.getnames()
        assert "app/main.py" in names
        assert "app/helper.py" in names

    def test_upload_archive_missing_credentials_returns_empty(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        client = SpacesClient()
        result = client.upload_archive("app", {"main.py": "pass"})
        assert result == ""

    def test_upload_archive_boto_exception_returns_empty(self):
        client = _make_client()
        client._client.put_object.side_effect = RuntimeError("network error")
        result = client.upload_archive("app", {"main.py": "pass"})
        assert result == ""


class TestListArtifacts:
    def test_list_artifacts_returns_objects(self):
        client = _make_client()
        last_mod = datetime(2026, 3, 17, 12, 0, 0)
        client._client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "myapp/myapp.tar.gz", "Size": 1024, "LastModified": last_mod},
                {"Key": "myapp/spec.json", "Size": 256, "LastModified": last_mod},
            ]
        }
        results = client.list_artifacts("myapp/")
        assert len(results) == 2
        assert results[0]["key"] == "myapp/myapp.tar.gz"
        assert results[0]["size"] == 1024
        assert results[0]["last_modified"] == last_mod.isoformat()
        assert "myapp/myapp.tar.gz" in results[0]["url"]
        assert results[1]["key"] == "myapp/spec.json"

    def test_list_artifacts_empty_prefix_returns_all(self):
        client = _make_client()
        client._client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "a/b.tar.gz", "Size": 100, "LastModified": datetime(2026, 1, 1)},
            ]
        }
        results = client.list_artifacts("")
        assert len(results) == 1

    def test_list_artifacts_no_contents_returns_empty_list(self):
        client = _make_client()
        client._client.list_objects_v2.return_value = {}
        results = client.list_artifacts("missing/")
        assert results == []

    def test_list_artifacts_missing_credentials_returns_empty(self, monkeypatch):
        monkeypatch.delenv("DO_SPACES_KEY", raising=False)
        monkeypatch.delenv("DO_SPACES_SECRET", raising=False)
        client = SpacesClient()
        results = client.list_artifacts("any/")
        assert results == []

    def test_list_artifacts_boto_exception_returns_empty(self):
        client = _make_client()
        client._client.list_objects_v2.side_effect = Exception("timeout")
        results = client.list_artifacts("prefix/")
        assert results == []
