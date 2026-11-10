"""Génération de fichiers CSV de transactions financières.

Les données sont volontairement NON aléatoires : on connaît à l'avance les totaux
attendus, ce qui permet d'écrire des tests précis sur la pipeline.
"""
import argparse
import csv
from pathlib import Path
from typing import NamedTuple

COLUMNS = [
    "datetime_transaction",
    "iban_origine",
    "pays_source",
    "banque_source",
    "iban_destinataire",
    "pays_destinataire",
    "montant_eur",
]


class Transaction(NamedTuple):
    datetime_transaction: str  # ISO 8601, ex. "2026-01-05T09:00:00"
    iban_origine: str
    pays_source: str
    banque_source: str
    iban_destinataire: str
    pays_destinataire: str
    montant_eur: str  # chaîne à 2 décimales, évite les erreurs de flottants


# IBAN fictifs (non réels), réutilisés pour avoir des cumuls prévisibles.
IBAN_A = "FR7630004000031234567890143"  # BNP, France
IBAN_B = "FR7612548029981234567890161"  # Crédit Agricole, France
IBAN_C = "DE89370400440532013000"  # Deutsche Bank, Allemagne
IBAN_D = "ES9121000418450200051332"  # CaixaBank, Espagne
IBAN_E = "FR7610278060321234567890185"  # Crédit Mutuel, France

BNP, CA, DB, CAIXA, CM = (
    "BNP Paribas",
    "Crédit Agricole",
    "Deutsche Bank",
    "CaixaBank",
    "Crédit Mutuel",
)

# Un "batch" = un fichier CSV. Les cas limites sont là exprès :
#  - 5000.00 pile (NE doit PAS être flaggé), 5000.01 (doit l'être)
#  - IBAN_A émet plusieurs fois, IBAN_B reçoit plusieurs fois (cumuls)
BATCHES: dict[str, list[Transaction]] = {
    "transactions_001.csv": [
        Transaction("2026-01-05T09:00:00", IBAN_A, "FR", BNP, IBAN_B, "FR", "1200.00"),
        Transaction("2026-01-05T10:30:00", IBAN_A, "FR", BNP, IBAN_C, "DE", "800.50"),
        Transaction("2026-01-05T11:15:00", IBAN_B, "FR", CA, IBAN_D, "ES", "5000.00"),
        Transaction("2026-01-05T14:00:00", IBAN_B, "FR", CA, IBAN_A, "FR", "5000.01"),
        Transaction("2026-01-05T15:45:00", IBAN_C, "DE", DB, IBAN_B, "FR", "150.00"),
        Transaction("2026-01-05T16:20:00", IBAN_A, "FR", BNP, IBAN_E, "FR", "12000.00"),
        Transaction("2026-01-05T17:00:00", IBAN_D, "ES", CAIXA, IBAN_B, "FR", "49.99"),
    ],
    "transactions_002.csv": [
        Transaction("2026-01-06T08:10:00", IBAN_E, "FR", CM, IBAN_A, "FR", "300.00"),
        Transaction("2026-01-06T09:45:00", IBAN_C, "DE", DB, IBAN_D, "ES", "7500.00"),
        Transaction("2026-01-06T12:00:00", IBAN_A, "FR", BNP, IBAN_B, "FR", "20.00"),
        Transaction("2026-01-06T13:30:00", IBAN_B, "FR", CA, IBAN_C, "DE", "4999.99"),
        Transaction("2026-01-06T18:05:00", IBAN_D, "ES", CAIXA, IBAN_A, "FR", "250.75"),
    ],
}


def write_csv(path: Path, transactions: list[Transaction]) -> None:
    """Écrit une liste de transactions dans un fichier CSV (c'est la partie I/O)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(transactions)


def generate_all(out_dir: Path) -> list[Path]:
    """Génère tous les CSV dans out_dir et renvoie leurs chemins."""
    paths = []
    for name, transactions in BATCHES.items():
        path = out_dir / name
        write_csv(path, transactions)
        paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère des CSV de transactions.")
    parser.add_argument("--out", type=Path, default=Path("data/incoming"))
    args = parser.parse_args()
    for path in generate_all(args.out):
        print(f"écrit : {path}")


if __name__ == "__main__":
    main()
