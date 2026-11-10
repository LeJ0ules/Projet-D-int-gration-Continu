from datetime import datetime
from decimal import Decimal

from src.models import Transaction
from src.transforms import (
    flag_transactions,
    process,
    sum_received_by_iban,
    sum_sent_by_bank,
    sum_sent_by_iban,
)


def tx(origine, banque, dest, montant):
    return Transaction(
        datetime_transaction=datetime(2026, 1, 5, 9, 0, 0),
        iban_origine=origine,
        pays_source="FR",
        banque_source=banque,
        iban_destinataire=dest,
        pays_destinataire="FR",
        montant_eur=Decimal(montant),
    )


# Petit jeu de données écrit à la main : les résultats attendus se calculent de tête.
TXS = [
    tx("A", "BNP", "B", "100.00"),
    tx("A", "BNP", "C", "50.50"),
    tx("B", "CA", "C", "5000.00"),
    tx("B", "CA", "A", "5000.01"),
]


def test_sum_sent_by_iban():
    assert sum_sent_by_iban(TXS) == {"A": Decimal("150.50"), "B": Decimal("10000.01")}


def test_sum_sent_by_bank():
    assert sum_sent_by_bank(TXS) == {"BNP": Decimal("150.50"), "CA": Decimal("10000.01")}


def test_sum_received_by_iban():
    assert sum_received_by_iban(TXS) == {
        "B": Decimal("100.00"),
        "C": Decimal("5050.50"),
        "A": Decimal("5000.01"),
    }


def test_flag_is_strictly_above_threshold():
    flags = [t.flagged for t in flag_transactions(TXS)]
    assert flags == [False, False, False, True]  # 5000.00 pile n'est PAS flaggé


def test_flag_does_not_mutate_input():
    flag_transactions(TXS)
    assert not any(t.flagged for t in TXS)


def test_empty_input():
    assert sum_sent_by_iban([]) == {}
    assert flag_transactions([]) == []


def test_process_groups_all_results():
    result = process(TXS)
    assert len(result.transactions) == 4
    assert result.sent_by_bank["CA"] == Decimal("10000.01")
