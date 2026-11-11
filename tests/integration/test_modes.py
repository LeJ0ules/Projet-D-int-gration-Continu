"""Les 3 modes de la pipeline : en production, un job "seed" simule l'arrivée de fichiers
et le CronJob tourne en mode "process" (il ne génère jamais de données)."""
from src.pipeline import run
from src.s3 import list_csv_keys, make_client

F1, F2 = "transactions_001.csv", "transactions_002.csv"


def count(conn, table: str) -> int:
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_seed_mode_only_uploads_files(conn, database_url, s3_settings):
    summary = run(database_url, s3_settings, mode="seed")
    assert summary.processed == [] and summary.skipped == []
    assert len(list_csv_keys(make_client(s3_settings), s3_settings.bucket)) == 2
    assert count(conn, "processed_files") == 0  # rien n'a été traité


def test_process_mode_never_generates_data(conn, database_url, s3_settings):
    summary = run(database_url, s3_settings, mode="process")
    assert summary.processed == []
    assert list_csv_keys(make_client(s3_settings), s3_settings.bucket) == []


def test_seed_then_process_then_process_again(conn, database_url, s3_settings):
    run(database_url, s3_settings, mode="seed")
    first = run(database_url, s3_settings, mode="process")
    assert sorted(first.processed) == [F1, F2]
    assert count(conn, "transactions") == 12

    second = run(database_url, s3_settings, mode="process")  # le CronJob se relance
    assert second.processed == []
    assert sorted(second.skipped) == [F1, F2]
    assert count(conn, "transactions") == 12
