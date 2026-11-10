from datetime import datetime
from decimal import Decimal

from src.generate import IBAN_A, IBAN_B, IBAN_C, IBAN_D, generate_all
from src.loaders import load_transactions
from src.transforms import process


def test_load_converts_types(tmp_path):
    path = generate_all(tmp_path)[0]
    transactions = load_transactions(path)
    assert len(transactions) == 7
    first = transactions[0]
    assert first.datetime_transaction == datetime(2026, 1, 5, 9, 0, 0)
    assert first.montant_eur == Decimal("1200.00")
    assert first.flagged is False


def test_expected_results_on_first_generated_file(tmp_path):
    """Valeurs attendues calculées à la main à partir de transactions_001.csv."""
    result = process(load_transactions(generate_all(tmp_path)[0]))

    assert result.sent_by_iban == {
        IBAN_A: Decimal("14000.50"),  # 1200.00 + 800.50 + 12000.00
        IBAN_B: Decimal("10000.01"),  # 5000.00 + 5000.01
        IBAN_C: Decimal("150.00"),
        IBAN_D: Decimal("49.99"),
    }
    assert result.sent_by_bank["BNP Paribas"] == Decimal("14000.50")
    assert result.received_by_iban[IBAN_B] == Decimal("1399.99")  # 1200 + 150 + 49.99

    flagged = [t.montant_eur for t in result.transactions if t.flagged]
    assert flagged == [Decimal("5000.01"), Decimal("12000.00")]
