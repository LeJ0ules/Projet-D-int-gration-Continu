"""Orchestration : génère les CSV, les dépose dans S3, les récupère, les traite, les insère.

Ce fichier ne contient pas de logique métier : il enchaîne les briques
(generate -> s3 -> loaders -> transforms -> db) dans le bon ordre.
"""
import argparse
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

# "all"     : génère + dépose dans S3 + traite (CI, démo locale)
# "seed"    : génère + dépose dans S3 seulement (simule l'arrivée de fichiers)
# "process" : traite seulement ce qui est déjà dans S3 (production : le CronJob)
MODES = ("all", "seed", "process")


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
    mode: str = "all",
    attempts: int = 3,
    wait_seconds: float = 1.0,
) -> RunSummary:
    if mode not in MODES:
        raise ValueError(f"mode inconnu : {mode!r} (attendu : {', '.join(MODES)})")
    retry = {"attempts": attempts, "wait_seconds": wait_seconds}
    client = s3.make_client(s3_settings)
    s3.ensure_bucket(client, s3_settings.bucket, **retry)
    if mode in ("all", "seed"):
        upload_generated_files(client, s3_settings.bucket, **retry)
    if mode == "seed":
        return RunSummary()
    with db.connect(database_url) as conn:
        db.init_schema(conn)
    return process_bucket(database_url, client, s3_settings.bucket, **retry)


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Pipeline CSV -> S3 -> PostgreSQL.")
    parser.add_argument("--mode", choices=MODES, default="all")
    args = parser.parse_args(argv)
    summary = run(os.environ["DATABASE_URL"], S3Settings.from_env(), mode=args.mode)
    print(f"traités : {summary.processed}")
    print(f"ignorés (déjà traités) : {summary.skipped}")


if __name__ == "__main__":
    main()
