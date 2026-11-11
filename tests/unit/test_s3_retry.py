"""Retry sur le téléchargement S3, testé avec un faux client (aucun serveur nécessaire)."""
import io

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from src.s3 import S3Settings, download_bytes, make_client


class FakeClient:
    """Échoue `failures` fois avec `error`, puis renvoie un contenu."""

    def __init__(self, failures: int, error: Exception):
        self.failures, self.error, self.calls = failures, error, 0

    def get_object(self, Bucket, Key):  # noqa: N803 (signature identique à boto3)
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return {"Body": io.BytesIO(b"contenu")}


def client_error(status: int, code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "x"}, "ResponseMetadata": {"HTTPStatusCode": status}},
        "GetObject",
    )


def fetch(client):
    return download_bytes(client, "bucket", "incoming/a.csv", attempts=3, wait_seconds=0)


def test_recovers_after_connection_errors():
    client = FakeClient(2, EndpointConnectionError(endpoint_url="http://s3"))
    assert fetch(client) == b"contenu"
    assert client.calls == 3


def test_gives_up_after_max_attempts():
    client = FakeClient(99, EndpointConnectionError(endpoint_url="http://s3"))
    with pytest.raises(EndpointConnectionError):
        fetch(client)
    assert client.calls == 3


def test_retries_on_server_error_5xx():
    client = FakeClient(1, client_error(503, "ServiceUnavailable"))
    assert fetch(client) == b"contenu"
    assert client.calls == 2


def test_does_not_retry_on_missing_file_404():
    client = FakeClient(99, client_error(404, "NoSuchKey"))
    with pytest.raises(ClientError):
        fetch(client)
    assert client.calls == 1  # inutile de réessayer un fichier qui n'existe pas


def test_unreachable_endpoint_fails_after_retries():
    # Port 1 : rien n'écoute, la connexion est refusée immédiatement.
    client = make_client(S3Settings("http://127.0.0.1:1", "k", "s"))
    with pytest.raises(EndpointConnectionError):
        download_bytes(client, "bucket", "incoming/a.csv", attempts=2, wait_seconds=0)
