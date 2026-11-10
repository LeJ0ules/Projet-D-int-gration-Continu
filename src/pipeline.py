"""Orchestration : génère les CSV, les traite, les insère en base.

Ce fichier ne contient pas de logique métier : il enchaîne les briques
(generate -> loaders -> transforms -> db) dans le bon ordre.
"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import psycopg

from src import db
from src.generate import generate_all
from src.loaders import file_sha256, load_transactions
from src.transforms import process


@dataclass
class RunSummary:
    processed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def process_directory(
    database_url: str, data_dir: Path, *, attempts: int = 3, wait_seconds: float = 1.0
) -> RunSummary:
    """Traite chaque CSV du dossier, sauf ceux déjà traités (repérés par leur hash)."""
    summary = RunSummary()
    for path in sorted(data_dir.glob("*.csv")):
        file_hash = file_sha256(path)
        with db.connect(database_url) as conn:
            already_done = db.is_file_processed(conn, file_hash)
        if already_done:
            summary.skipped.append(path.name)
            continue
        result = process(load_transactions(path))
        try:
            db.insert_result_with_retry(
                database_url,
                file_hash,
                path.name,
                result,
                attempts=attempts,
                wait_seconds=wait_seconds,
            )
        except psycopg.errors.UniqueViolation:
            # Fichier déjà enregistré : soit un autre process l'a inséré entre-temps,
            # soit un essai précédent avait réussi mais sa réponse s'est perdue.
            summary.skipped.append(path.name)
            continue
        summary.processed.append(path.name)
    return summary


def run(
    database_url: str, data_dir: Path, *, attempts: int = 3, wait_seconds: float = 1.0
) -> RunSummary:
    generate_all(data_dir)
    with db.connect(database_url) as conn:
        db.init_schema(conn)
    return process_directory(database_url, data_dir, attempts=attempts, wait_seconds=wait_seconds)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    database_url = os.environ["DATABASE_URL"]
    data_dir = Path(os.environ.get("DATA_DIR", "data/incoming"))
    summary = run(database_url, data_dir)
    print(f"traités : {summary.processed}")
    print(f"ignorés (déjà traités) : {summary.skipped}")


if __name__ == "__main__":
    main()
