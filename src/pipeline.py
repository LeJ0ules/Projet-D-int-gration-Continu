"""Orchestration : génère les CSV, les dépose dans S3, les récupère, les traite, les insère.

Ce fichier ne contient pas de logique métier : il enchaîne les briques
(generate -> s3 -> loaders -> transforms -> db) dans le bon ordre.
"""
import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg

from src import db, s3
from src.generate import generate_all
from src.loaders import parse_transactions, sha256_bytes
from src.s3 import PREFIX, S3Settings
from src.transforms import process


@dataclass
class RunSummary:
    processed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def upload_generated_files(client: Any, bucket: str, **retry: Any) -> list[str]:
    """Génère les CSV dans un dossier temporaire puis les dépose dans le bucket."""
    keys = []
    with tempfile.TemporaryDirectory() as tmp:
        for path in generate_all(Path(tmp)):
            key = f"{PREFIX}{path.name}"
            s3.upload_file(client, bucket, path, key, **retry)
            keys.append(key)
    return keys


def process_bucket(
    database_url: str, client: Any, bucket: str, *, attempts: int = 3, wait_seconds: float = 1.0
) -> RunSummary:
    """Traite chaque CSV du bucket, sauf ceux déjà traités (repérés par leur hash)."""
    retry = {"attempts": attempts, "wait_seconds": wait_seconds}
    summary = RunSummary()
    for key in s3.list_csv_keys(client, bucket, **retry):
        name = key.removeprefix(PREFIX)
        content = s3.download_bytes(client, bucket, key, **retry)  # avec retry
        file_hash = sha256_bytes(content)
        with db.connect(database_url) as conn:
            already_done = db.is_file_processed(conn, file_hash)
        if already_done:
            summary.skipped.append(name)
            continue
        result = process(parse_transactions(content))
        try:
            db.insert_result_with_retry(database_url, file_hash, name, result, **retry)
        except psycopg.errors.UniqueViolation:
            # Fichier déjà enregistré : soit un autre process l'a inséré entre-temps,
            # soit un essai précédent avait réussi mais sa réponse s'est perdue.
            summary.skipped.append(name)
            continue
        summary.processed.append(name)
    return summary


def run(
    database_url: str,
    s3_settings: S3Settings,
    *,
    attempts: int = 3,
    wait_seconds: float = 1.0,
) -> RunSummary:
    retry = {"attempts": attempts, "wait_seconds": wait_seconds}
    client = s3.make_client(s3_settings)
    s3.ensure_bucket(client, s3_settings.bucket, **retry)
    upload_generated_files(client, s3_settings.bucket, **retry)
    with db.connect(database_url) as conn:
        db.init_schema(conn)
    return process_bucket(database_url, client, s3_settings.bucket, **retry)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summary = run(os.environ["DATABASE_URL"], S3Settings.from_env())
    print(f"traités : {summary.processed}")
    print(f"ignorés (déjà traités) : {summary.skipped}")


if __name__ == "__main__":
    main()
