"""Tests d'intégration : on lance la vraie pipeline sur une vraie base PostgreSQL,
puis on vérifie les valeurs stockées. Les valeurs attendues sont calculées à la main
à partir des données de src/generate.py."""
from decimal import Decimal

from src.generate import IBAN_A, IBAN_B, IBAN_C, IBAN_D, IBAN_E
from src.pipeline import run

F1 = "transactions_001.csv"
F2 = "transactions_002.csv"


def d(value: str) -> Decimal:
    return Decimal(value)


def sums(conn, table: str, key: str, file_name: str) -> dict:
    rows = conn.execute(
        f"""SELECT s.{key}, s.total_eur FROM {table} s
            JOIN processed_files p USING (file_hash) WHERE p.file_name = %s""",
        (file_name,),
    ).fetchall()
    return dict(rows)


def flagged_amounts(conn, file_name: str) -> list[Decimal]:
    rows = conn.execute(
        """SELECT t.montant_eur FROM transactions t
           JOIN processed_files p USING (file_hash)
           WHERE p.file_name = %s AND t.flagged ORDER BY t.montant_eur""",
        (file_name,),
    ).fetchall()
    return [r[0] for r in rows]


def test_row_counts(conn, database_url, tmp_path):
    run(database_url, tmp_path)
    assert conn.execute("SELECT count(*) FROM processed_files").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 12  # 7 + 5


def test_sums_file_1(conn, database_url, tmp_path):
    run(database_url, tmp_path)
    assert sums(conn, "sum_sent_by_iban", "iban", F1) == {
        IBAN_A: d("14000.50"),
        IBAN_B: d("10000.01"),
        IBAN_C: d("150.00"),
        IBAN_D: d("49.99"),
    }
    assert sums(conn, "sum_sent_by_bank", "bank", F1) == {
        "BNP Paribas": d("14000.50"),
        "Crédit Agricole": d("10000.01"),
        "Deutsche Bank": d("150.00"),
        "CaixaBank": d("49.99"),
    }
    assert sums(conn, "sum_received_by_iban", "iban", F1) == {
        IBAN_A: d("5000.01"),
        IBAN_B: d("1399.99"),
        IBAN_C: d("800.50"),
        IBAN_D: d("5000.00"),
        IBAN_E: d("12000.00"),
    }


def test_sums_file_2(conn, database_url, tmp_path):
    run(database_url, tmp_path)
    assert sums(conn, "sum_sent_by_iban", "iban", F2) == {
        IBAN_E: d("300.00"),
        IBAN_C: d("7500.00"),
        IBAN_A: d("20.00"),
        IBAN_B: d("4999.99"),
        IBAN_D: d("250.75"),
    }
    assert sums(conn, "sum_received_by_iban", "iban", F2) == {
        IBAN_A: d("550.75"),
        IBAN_D: d("7500.00"),
        IBAN_B: d("20.00"),
        IBAN_C: d("4999.99"),
    }


def test_flags(conn, database_url, tmp_path):
    run(database_url, tmp_path)
    assert flagged_amounts(conn, F1) == [d("5000.01"), d("12000.00")]
    assert flagged_amounts(conn, F2) == [d("7500.00")]
    # Cas limite : 5000.00 pile n'est PAS flaggé.
    row = conn.execute("SELECT flagged FROM transactions WHERE montant_eur = 5000.00").fetchone()
    assert row[0] is False


def test_second_run_does_not_reprocess(conn, database_url, tmp_path):
    run(database_url, tmp_path)
    second = run(database_url, tmp_path)
    assert second.processed == []
    assert sorted(second.skipped) == [F1, F2]
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 12


def test_renamed_copy_is_not_reprocessed(conn, database_url, tmp_path):
    run(database_url, tmp_path)
    (tmp_path / "copie.csv").write_bytes((tmp_path / F1).read_bytes())
    second = run(database_url, tmp_path)
    assert "copie.csv" in second.skipped
    assert conn.execute("SELECT count(*) FROM transactions").fetchone()[0] == 12
