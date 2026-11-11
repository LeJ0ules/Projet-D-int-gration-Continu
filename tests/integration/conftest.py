import os

import pytest

from src import db, s3

TABLES = (
    "sum_received_by_iban, sum_sent_by_bank, sum_sent_by_iban, transactions, processed_files"
)


def skip_or_fail(message: str) -> None:
    # En CI, un service absent est une ERREUR (sinon les tests seraient ignorés en silence
    # et la CI resterait verte à tort). En local, on ignore simplement ces tests.
    if os.environ.get("CI"):
        pytest.fail(message)
    pytest.skip(message)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        skip_or_fail("DATABASE_URL n'est pas défini")
    return url


@pytest.fixture
def conn(database_url):
    """Connexion à une base VIDE : on repart de zéro avant chaque test."""
    with db.connect(database_url) as connection:
        db.init_schema(connection)
        connection.execute(f"TRUNCATE {TABLES}")
        connection.commit()
        yield connection


@pytest.fixture
def s3_settings() -> s3.S3Settings:
    """Réglages S3 ; le bucket existe et est VIDE au début de chaque test."""
    if not os.environ.get("S3_ENDPOINT_URL"):
        skip_or_fail("S3_ENDPOINT_URL n'est pas défini")
    settings = s3.S3Settings.from_env()
    client = s3.make_client(settings)
    s3.ensure_bucket(client, settings.bucket)
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=settings.bucket):
        for obj in page.get("Contents", []):
            client.delete_object(Bucket=settings.bucket, Key=obj["Key"])
    return settings
