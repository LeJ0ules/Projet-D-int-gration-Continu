import csv

from src.generate import BATCHES, COLUMNS, generate_all


def read_rows(path):
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_generates_several_files_with_5_to_10_rows(tmp_path):
    paths = generate_all(tmp_path)
    assert len(paths) >= 2
    for path in paths:
        assert 5 <= len(read_rows(path)) <= 10


def test_header_matches_expected_columns(tmp_path):
    for path in generate_all(tmp_path):
        with path.open(encoding="utf-8") as f:
            assert next(csv.reader(f)) == COLUMNS


def test_generation_is_deterministic(tmp_path):
    first = generate_all(tmp_path / "run1")
    second = generate_all(tmp_path / "run2")
    for a, b in zip(first, second, strict=True):
        assert a.read_bytes() == b.read_bytes()


def test_boundary_amounts_are_present(tmp_path):
    amounts = {row["montant_eur"] for p in generate_all(tmp_path) for row in read_rows(p)}
    assert {"5000.00", "5000.01", "4999.99"} <= amounts


def test_batches_are_not_empty():
    assert all(BATCHES.values())
