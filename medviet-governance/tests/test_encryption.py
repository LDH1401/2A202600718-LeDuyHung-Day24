# tests/test_encryption.py
import os
import tempfile

import pandas as pd
import pytest

from src.encryption.vault import SimpleVault


@pytest.fixture
def vault():
    path = os.path.join(tempfile.gettempdir(), ".vault_key_pytest")
    if os.path.exists(path):
        os.remove(path)
    return SimpleVault(master_key_path=path)


def test_round_trip(vault):
    original = "Nguyen Van A - CCCD: 012345678901"
    payload = vault.encrypt_data(original)
    assert payload["algorithm"] == "AES-256-GCM"
    assert original not in payload["ciphertext"]
    assert vault.decrypt_data(payload) == original


def test_unique_dek_per_encryption(vault):
    a = vault.encrypt_data("same text")
    b = vault.encrypt_data("same text")
    # DEK & nonce ngẫu nhiên -> ciphertext khác nhau dù plaintext giống
    assert a["ciphertext"] != b["ciphertext"]
    assert vault.decrypt_data(a) == vault.decrypt_data(b) == "same text"


def test_encrypt_column(vault):
    df = pd.DataFrame({"cccd": ["012345678901", "111122223333"]})
    enc = vault.encrypt_column(df, "cccd")
    assert "012345678901" not in enc["cccd"].iloc[0]
    assert "encrypted_dek" in enc["cccd"].iloc[0]
