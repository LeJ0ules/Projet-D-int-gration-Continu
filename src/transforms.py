"""Traitement des données : fonctions PURES uniquement.

Pure = mêmes entrées -> mêmes sorties, aucun accès fichier/réseau/base,
aucune modification des arguments. C'est ce qui les rend faciles à tester.
"""
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from decimal import Decimal

from src.models import Transaction

FLAG_THRESHOLD = Decimal("5000")


def sum_sent_by_iban(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    """Somme des montants envoyés, par IBAN d'origine."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for t in transactions:
        totals[t.iban_origine] += t.montant_eur
    return dict(totals)


def sum_sent_by_bank(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    """Somme des montants envoyés, par banque source."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for t in transactions:
        totals[t.banque_source] += t.montant_eur
    return dict(totals)


def sum_received_by_iban(transactions: Iterable[Transaction]) -> dict[str, Decimal]:
    """Somme des montants reçus, par IBAN destinataire."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for t in transactions:
        totals[t.iban_destinataire] += t.montant_eur
    return dict(totals)


def flag_transactions(
    transactions: Iterable[Transaction], threshold: Decimal = FLAG_THRESHOLD
) -> list[Transaction]:
    """Renvoie de nouvelles transactions, `flagged=True` si montant > seuil (strict)."""
    return [replace(t, flagged=t.montant_eur > threshold) for t in transactions]


@dataclass(frozen=True)
class ProcessingResult:
    """Tout ce qu'on insérera ensuite en base."""

    transactions: list[Transaction]
    sent_by_iban: dict[str, Decimal]
    sent_by_bank: dict[str, Decimal]
    received_by_iban: dict[str, Decimal]


def process(transactions: list[Transaction]) -> ProcessingResult:
    """Applique tous les traitements et regroupe les résultats."""
    return ProcessingResult(
        transactions=flag_transactions(transactions),
        sent_by_iban=sum_sent_by_iban(transactions),
        sent_by_bank=sum_sent_by_bank(transactions),
        received_by_iban=sum_received_by_iban(transactions),
    )
