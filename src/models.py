"""Modèle de données utilisé par le chargement et le traitement."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Transaction:
    """Une transaction "typée" (dates et montants convertis), immuable.

    `frozen=True` : on ne peut pas la modifier après création. Les fonctions de
    traitement créent donc de nouveaux objets au lieu de modifier les anciens,
    ce qui garantit qu'elles restent pures.
    """

    datetime_transaction: datetime
    iban_origine: str
    pays_source: str
    banque_source: str
    iban_destinataire: str
    pays_destinataire: str
    montant_eur: Decimal
    flagged: bool = False
