"""Accès à la base PostgreSQL (I/O). Aucune logique de calcul ici."""
from pathlib import Path

import psycopg

from src.transforms import ProcessingResult

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def init_schema(conn: psycopg.Connection) -> None:
    """Crée les tables si elles n'existent pas."""
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def is_file_processed(conn: psycopg.Connection, file_hash: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM processed_files WHERE file_hash = %s", (file_hash,)
    ).fetchone()
    return row is not None


def insert_result(
    conn: psycopg.Connection, file_hash: str, file_name: str, result: ProcessingResult
) -> None:
    """Insère TOUT le résultat d'un fichier dans UNE SEULE transaction SQL.

    Soit tout est enregistré (y compris la ligne `processed_files`), soit rien.
    Si le fichier a déjà été traité, la clé primaire de `processed_files` lève une
    erreur et tout est annulé : impossible de traiter deux fois le même fichier,
    même si deux exécutions tournent en parallèle.
    """
    try:
        _insert_all(conn, file_hash, file_name, result)
    except Exception:
        conn.rollback()  # on laisse la connexion propre pour un éventuel retry
        raise
    conn.commit()  # sans ce commit, rien n'est durable si une transaction était déjà ouverte


def _insert_all(
    conn: psycopg.Connection, file_hash: str, file_name: str, result: ProcessingResult
) -> None:
    with conn.transaction():
        # processed_files d'abord : les autres tables y font référence (clé étrangère).
        conn.execute(
            "INSERT INTO processed_files (file_hash, file_name) VALUES (%s, %s)",
            (file_hash, file_name),
        )
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO transactions
                   (file_hash, datetime_transaction, iban_origine, pays_source,
                    banque_source, iban_destinataire, pays_destinataire,
                    montant_eur, flagged)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                [
                    (
                        file_hash,
                        t.datetime_transaction,
                        t.iban_origine,
                        t.pays_source,
                        t.banque_source,
                        t.iban_destinataire,
                        t.pays_destinataire,
                        t.montant_eur,
                        t.flagged,
                    )
                    for t in result.transactions
                ],
            )
            for table, column, totals in (
                ("sum_sent_by_iban", "iban", result.sent_by_iban),
                ("sum_sent_by_bank", "bank", result.sent_by_bank),
                ("sum_received_by_iban", "iban", result.received_by_iban),
            ):
                cur.executemany(
                    f"INSERT INTO {table} (file_hash, {column}, total_eur) VALUES (%s, %s, %s)",
                    [(file_hash, key, total) for key, total in totals.items()],
                )
