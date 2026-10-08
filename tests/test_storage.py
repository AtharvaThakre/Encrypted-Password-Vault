"""
tests/test_storage.py
---------------------
Tests for vault/storage.py.

Uses tmp_path (pytest fixture) to avoid touching the real filesystem.
No real passwords or secrets are used; test data is clearly fake.
"""

import json
import base64
import pytest
from pathlib import Path

from vault.storage import (
    load_vault_file,
    save_vault_file,
    entries_to_bytes,
    bytes_to_entries,
    vault_exists,
    VAULT_VERSION,
    VAULT_KDF,
)
from vault.crypto import derive_key, encrypt, decrypt, generate_salt, SALT_LENGTH


FAKE_SALT = b"\x11" * SALT_LENGTH
FAKE_KEY = derive_key("StorageTestPass!1", FAKE_SALT)


# ---------------------------------------------------------------------------
# vault_exists
# ---------------------------------------------------------------------------

class TestVaultExists:
    def test_returns_false_when_missing(self, tmp_path):
        assert not vault_exists(tmp_path / "vault.enc")

    def test_returns_true_when_file_present(self, tmp_path):
        p = tmp_path / "vault.enc"
        p.write_text("{}")
        assert vault_exists(p)


# ---------------------------------------------------------------------------
# save_vault_file / load_vault_file round-trip
# ---------------------------------------------------------------------------

class TestSaveLoad:
    PLAINTEXT = b"[test-vault-data]"

    def _make_vault(self, path):
        nonce, ciphertext = encrypt(FAKE_KEY, self.PLAINTEXT)
        save_vault_file(FAKE_SALT, nonce, ciphertext, path)
        return nonce, ciphertext

    def test_file_is_created(self, tmp_path):
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        assert path.exists()

    def test_round_trip_salt(self, tmp_path):
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        data = load_vault_file(path)
        assert data["salt"] == FAKE_SALT

    def test_round_trip_nonce_and_ciphertext(self, tmp_path):
        path = tmp_path / "vault.enc"
        nonce, ciphertext = self._make_vault(path)
        data = load_vault_file(path)
        assert data["nonce"] == nonce
        assert data["ciphertext"] == ciphertext

    def test_loaded_data_can_be_decrypted(self, tmp_path):
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        data = load_vault_file(path)
        recovered = decrypt(FAKE_KEY, data["nonce"], data["ciphertext"])
        assert recovered == self.PLAINTEXT

    def test_file_contains_no_plaintext_secrets(self, tmp_path):
        """The vault file must not contain any recognisable plaintext."""
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        raw = path.read_text()
        assert "test-vault-data" not in raw
        assert "password" not in raw.lower() or "kdf" in raw  # kdf field is ok

    def test_version_field_is_correct(self, tmp_path):
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        data = load_vault_file(path)
        assert data["version"] == VAULT_VERSION

    def test_kdf_field_is_correct(self, tmp_path):
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        data = load_vault_file(path)
        assert data["kdf"] == VAULT_KDF

    def test_atomic_write_does_not_leave_tmp(self, tmp_path):
        path = tmp_path / "vault.enc"
        self._make_vault(path)
        tmp = tmp_path / "vault.enc.tmp"
        assert not tmp.exists()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestLoadErrors:
    def test_missing_file_raises_filenotfound(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_vault_file(tmp_path / "nonexistent.enc")

    def test_corrupt_json_raises_valueerror(self, tmp_path):
        path = tmp_path / "vault.enc"
        path.write_text("NOT JSON")
        with pytest.raises(ValueError):
            load_vault_file(path)

    def test_missing_field_raises_valueerror(self, tmp_path):
        path = tmp_path / "vault.enc"
        path.write_text(json.dumps({"version": 1}))
        with pytest.raises(ValueError):
            load_vault_file(path)

    def test_wrong_version_raises_valueerror(self, tmp_path):
        path = tmp_path / "vault.enc"
        path.write_text(json.dumps({
            "version": 999,
            "kdf": "scrypt",
            "salt": "YQ==",
            "nonce": "YQ==",
            "ciphertext": "YQ==",
        }))
        with pytest.raises(ValueError, match="version"):
            load_vault_file(path)

    def test_wrong_kdf_raises_valueerror(self, tmp_path):
        path = tmp_path / "vault.enc"
        path.write_text(json.dumps({
            "version": 1,
            "kdf": "pbkdf2",
            "salt": "YQ==",
            "nonce": "YQ==",
            "ciphertext": "YQ==",
        }))
        with pytest.raises(ValueError, match="KDF"):
            load_vault_file(path)


# ---------------------------------------------------------------------------
# Entry serialisation helpers
# ---------------------------------------------------------------------------

class TestEntrySerialization:
    SAMPLE_ENTRIES = [
        {
            "id": "uuid-1",
            "website": "example.com",
            "username": "user@example.com",
            "password": "FakePassword!1",
            "notes": "test note",
        }
    ]

    def test_entries_to_bytes_produces_bytes(self):
        result = entries_to_bytes(self.SAMPLE_ENTRIES)
        assert isinstance(result, bytes)

    def test_round_trip(self):
        raw = entries_to_bytes(self.SAMPLE_ENTRIES)
        recovered = bytes_to_entries(raw)
        assert recovered == self.SAMPLE_ENTRIES

    def test_empty_list_round_trip(self):
        raw = entries_to_bytes([])
        assert bytes_to_entries(raw) == []

    def test_multiple_entries_round_trip(self):
        entries = self.SAMPLE_ENTRIES * 5
        assert bytes_to_entries(entries_to_bytes(entries)) == entries

    def test_invalid_bytes_raises_valueerror(self):
        with pytest.raises(ValueError):
            bytes_to_entries(b"not json")

    def test_non_list_json_raises_valueerror(self):
        with pytest.raises(ValueError):
            bytes_to_entries(b'{"key": "value"}')
