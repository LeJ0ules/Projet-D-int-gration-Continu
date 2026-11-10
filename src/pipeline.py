"""Orchestration : génère les CSV, les traite, les insère en base.

Ce fichier ne contient pas de logique métier : il enchaîne les briques
(generate -> loaders -> transforms -> db) dans le bon ordre.
"""
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


def process_directory(conn: psycopg.Connection, data_dir: Path) -> RunSummary:
    """Traite chaque CSV du dossier, sauf ceux déjà traités (repérés par leur hash)."""
    summary = RunSummary()
    for path in sorted(data_dir.glob("*.csv")):
        file_hash = file_sha256(path)
        if db.is_file_processed(conn, file_hash):
            summary.skipped.append(path.name)
            continue
        result = process(load_transactions(path))
        try:
            db.insert_result(conn, file_hash, path.name, result)
        except psycopg.errors.UniqueViolation:
            # Un autre process a inséré ce fichier entre notre vérification et l'insertion.
            summary.skipped.append(path.name)
            continue
        summary.processed.append(path.name)
    return summary


def run(database_url: str, data_dir: Path) -> RunSummary:
    generate_all(data_dir)
    with db.connect(database_url) as conn:
        db.init_schema(conn)
        return process_directory(conn, data_dir)


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    data_dir = Path(os.environ.get("DATA_DIR", "data/incoming"))
    summary = run(database_url, data_dir)
    print(f"traités : {summary.processed}")
    print(f"ignorés (déjà traités) : {summary.skipped}")


if __name__ == "__main__":
    main()
