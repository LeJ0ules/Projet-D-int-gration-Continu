"""Chargement des données (I/O). Aucune logique métier ici."""
import csv
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.models import Transaction


def parse_transactions(content: bytes) -> list[Transaction]:
    """Convertit le contenu d'un CSV (octets) en Transaction typées. Pure : aucun accès disque."""
    lines = content.decode("utf-8").splitlines()
    return [
        Transaction(
            datetime_transaction=datetime.fromisoformat(row["datetime_transaction"]),
            iban_origine=row["iban_origine"],
            pays_source=row["pays_source"],
            banque_source=row["banque_source"],
            iban_destinataire=row["iban_destinataire"],
            pays_destinataire=row["pays_destinataire"],
            montant_eur=Decimal(row["montant_eur"]),
        )
        for row in csv.DictReader(lines)
    ]


def load_transactions(path: Path) -> list[Transaction]:
    """Lit un CSV local et renvoie des Transaction typées (datetime, Decimal)."""
    return parse_transactions(path.read_bytes())


def sha256_bytes(content: bytes) -> str:
    """Empreinte SHA-256 d'un contenu : sert à repérer un fichier déjà traité."""
    return hashlib.sha256(content).hexdigest()


def file_sha256(path: Path) -> str:
    """Empreinte SHA-256 du contenu du fichier : sert à repérer un fichier déjà traité."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
