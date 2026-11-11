import pytest

from src.pipeline import run
from src.s3 import S3Settings


def test_unknown_mode_is_rejected_before_any_network_call():
    with pytest.raises(ValueError, match="mode inconnu"):
        run("postgresql://x", S3Settings("http://127.0.0.1:1", "k", "s"), mode="bogus")
