"""Simulation de bugs d'insertion et vérification du mécanisme de retry.

On remplace db.insert_result par une version défaillante (monkeypatch) pour simuler
une base qui coupe la connexion. wait_seconds=0 : pas d'attente réelle dans les tests.
"""
import psycopg
import pytest

from src import db
from src.pipeline import run

REAL_INSERT = db.insert_result


def count(conn, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_retry_recovers_from_transient_failures(conn, database_url, tmp_path, monkeypatch):
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        if len(calls) <= 2:  # les 2 premiers appels échouent
            raise psycopg.OperationalError("connexion coupée (simulée)")
        return REAL_INSERT(*args, **kwargs)

    monkeypatch.setattr(db, "insert_result", flaky)
    summary = run(database_url, tmp_path, attempts=3, wait_seconds=0)

    assert len(summary.processed) == 2
    assert len(calls) == 4  # fichier 1 : 3 essais (2 échecs + 1 succès), fichier 2 : 1 essai
    assert count(conn, "transactions") == 12  # aucune donnée en double


def test_gives_up_after_max_attempts_and_leaves_db_clean(conn, database_url, tmp_path, monkeypatch):
    calls = []

    def always_failing(*args, **kwargs):
        calls.append(1)
        raise psycopg.OperationalError("base indisponible (simulée)")

    monkeypatch.setattr(db, "insert_result", always_failing)
    with pytest.raises(psycopg.OperationalError):
        run(database_url, tmp_path, attempts=3, wait_seconds=0)

    assert len(calls) == 3
    assert count(conn, "processed_files") == 0  # rien d'enregistré
    assert count(conn, "transactions") == 0

    # La base redevient disponible : un nouveau lancement traite normalement les fichiers.
    monkeypatch.undo()
    summary = run(database_url, tmp_path, wait_seconds=0)
    assert len(summary.processed) == 2
    assert count(conn, "transactions") == 12


def test_retry_after_lost_ack_does_not_duplicate(conn, database_url, tmp_path, monkeypatch):
    """Pire cas : l'insertion RÉUSSIT mais la réponse se perd (erreur côté client).
    Le retry retombe sur un fichier déjà enregistré : il doit être ignoré, pas dupliqué."""
    state = {"first": True}

    def commit_then_error(*args, **kwargs):
        REAL_INSERT(*args, **kwargs)
        if state["first"]:
            state["first"] = False
            raise psycopg.OperationalError("réponse perdue après commit (simulée)")

    monkeypatch.setattr(db, "insert_result", commit_then_error)
    summary = run(database_url, tmp_path, attempts=3, wait_seconds=0)

    assert summary.skipped == ["transactions_001.csv"]
    assert summary.processed == ["transactions_002.csv"]
    assert count(conn, "processed_files") == 2
    assert count(conn, "transactions") == 12
