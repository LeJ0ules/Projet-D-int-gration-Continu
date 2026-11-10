"""Chargement des données (I/O). Aucune logique métier ici."""
import csv
import hashlib
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.models import Transaction


def load_transactions(path: Path) -> list[Transaction]:
    """Lit un CSV et renvoie des Transaction typées (datetime, Decimal)."""
    with path.open(newline="", encoding="utf-8") as f:
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
            for row in csv.DictReader(f)
        ]


def file_sha256(path: Path) -> str:
    """Empreinte SHA-256 du contenu du fichier : sert à repérer un fichier déjà traité."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
