import os

import pytest

from src import db

TABLES = (
    "sum_received_by_iban, sum_sent_by_bank, sum_sent_by_iban, transactions, processed_files"
)


@pytest.fixture
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        # En CI, une base absente est une ERREUR (sinon les tests seraient ignorés en silence
        # et la CI resterait verte à tort). En local, on ignore simplement ces tests.
        if os.environ.get("CI"):
            pytest.fail("DATABASE_URL n'est pas défini en CI")
        pytest.skip("DATABASE_URL non défini : tests d'intégration ignorés")
    return url


@pytest.fixture
def conn(database_url):
    """Connexion à une base VIDE : on repart de zéro avant chaque test."""
    with db.connect(database_url) as connection:
        db.init_schema(connection)
        connection.execute(f"TRUNCATE {TABLES}")
        connection.commit()
        yield connection
