"""Accès au stockage S3 (I/O) : envoi, listage et téléchargement des CSV.

Le code ne dépend pas d'un fournisseur : seule l'URL du endpoint change
(S3 local de la CI ou du cluster, S3 d'un cloud en production).
"""
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)
from tenacity import (
    Retrying,
    before_sleep_log,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

PREFIX = "incoming/"  # "dossier" du bucket où arrivent les CSV
T = TypeVar("T")


@dataclass(frozen=True)
class S3Settings:
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str = "transactions"

    @classmethod
    def from_env(cls) -> "S3Settings":
        return cls(
            endpoint_url=os.environ["S3_ENDPOINT_URL"],
            access_key=os.environ["S3_ACCESS_KEY"],
            secret_key=os.environ["S3_SECRET_KEY"],
            bucket=os.environ.get("S3_BUCKET", "transactions"),
        )


def make_client(settings: S3Settings) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        region_name="us-east-1",
        config=Config(
            # Les retries intégrés de boto3 sont coupés : c'est NOTRE mécanisme qui réessaie,
            # pour qu'il soit visible, configurable et testable.
            retries={"max_attempts": 0},
            connect_timeout=5,
            read_timeout=10,
            s3={"addressing_style": "path"},
        ),
    )


# Erreurs réseau "transitoires" : réessayer a du sens.
_NETWORK_ERRORS = (
    EndpointConnectionError,
    ConnectionClosedError,
    ConnectTimeoutError,
    ReadTimeoutError,
)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, _NETWORK_ERRORS):
        return True
    if isinstance(exc, ClientError):  # le serveur a répondu : on réessaie seulement si 5xx
        return exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0) >= 500
    return False  # ex. 404 "fichier inexistant" : inutile de réessayer


def call_with_retry(func: Callable[[], T], *, attempts: int = 3, wait_seconds: float = 1.0) -> T:
    """Exécute func ; la réessaie (attente exponentielle) si l'erreur est transitoire."""
    retrying = Retrying(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=wait_seconds, max=30),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    return retrying(func)


def ensure_bucket(client: Any, bucket: str, **retry: Any) -> None:
    def _ensure() -> None:
        try:
            client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            if exc.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                raise
            client.create_bucket(Bucket=bucket)

    call_with_retry(_ensure, **retry)


def upload_file(client: Any, bucket: str, path: Path, key: str, **retry: Any) -> None:
    body = path.read_bytes()
    call_with_retry(lambda: client.put_object(Bucket=bucket, Key=key, Body=body), **retry)


def list_csv_keys(client: Any, bucket: str, **retry: Any) -> list[str]:
    def _list() -> list[str]:
        keys: list[str] = []
        for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
            keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".csv")]
        return sorted(keys)

    return call_with_retry(_list, **retry)


def download_bytes(client: Any, bucket: str, key: str, **retry: Any) -> bytes:
    """Télécharge un objet ; la lecture complète est dans le retry (coupure en cours de route)."""
    return call_with_retry(
        lambda: client.get_object(Bucket=bucket, Key=key)["Body"].read(), **retry
    )
