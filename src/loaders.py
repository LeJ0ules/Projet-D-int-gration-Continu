"""Chargement des données (I/O). Aucune logique métier ici."""
import csv
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
