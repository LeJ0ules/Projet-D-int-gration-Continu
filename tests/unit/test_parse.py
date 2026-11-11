from src.generate import generate_all
from src.loaders import file_sha256, load_transactions, parse_transactions, sha256_bytes


def test_parse_bytes_gives_same_result_as_load_from_file(tmp_path):
    path = generate_all(tmp_path)[0]
    assert parse_transactions(path.read_bytes()) == load_transactions(path)


def test_sha256_bytes_matches_file_hash(tmp_path):
    path = generate_all(tmp_path)[0]
    assert sha256_bytes(path.read_bytes()) == file_sha256(path)
