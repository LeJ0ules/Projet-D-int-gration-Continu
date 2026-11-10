from src.loaders import file_sha256


def test_same_content_same_hash_even_with_different_names(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("x,y\n1,2\n")
    b.write_text("x,y\n1,2\n")
    assert file_sha256(a) == file_sha256(b)


def test_different_content_different_hash(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text("x,y\n1,2\n")
    b.write_text("x,y\n1,3\n")
    assert file_sha256(a) != file_sha256(b)
