"""Niveau 2 : les CSV transitent bien par le S3 local, et la pipeline lit depuis S3."""
import csv
import io
from decimal import Decimal

from src.generate import COLUMNS, IBAN_A, IBAN_B
from src.pipeline import run
from src.s3 import PREFIX, list_csv_keys, make_client


def test_generated_csvs_are_uploaded_to_s3(conn, database_url, s3_settings):
    run(database_url, s3_settings)
    keys = list_csv_keys(make_client(s3_settings), s3_settings.bucket)
    assert keys == [f"{PREFIX}transactions_001.csv", f"{PREFIX}transactions_002.csv"]


def test_pipeline_reads_files_from_s3(conn, database_url, s3_settings):
    """Un fichier déposé directement dans le bucket (jamais présent sur le disque local)
    est bien récupéré et traité."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    writer.writerow(["2026-02-01T10:00:00", IBAN_A, "FR", "BNP Paribas", IBAN_B, "FR", "99.90"])
    client = make_client(s3_settings)
    client.put_object(
        Bucket=s3_settings.bucket, Key=f"{PREFIX}extra.csv", Body=buffer.getvalue().encode()
    )

    summary = run(database_url, s3_settings)

    names = ["extra.csv", "transactions_001.csv", "transactions_002.csv"]
    assert sorted(summary.processed) == names
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 13  # 7 + 5 + 1
    row = conn.execute(
        """SELECT s.total_eur FROM sum_sent_by_iban s JOIN processed_files p USING (file_hash)
           WHERE p.file_name = 'extra.csv' AND s.iban = %s""",
        (IBAN_A,),
    ).fetchone()
    assert row[0] == Decimal("99.90")
