"""
tests/test_crypto.py
--------------------
Tests for vault/crypto.py.

SECURITY NOTE: No real passwords or secrets are used.
Test values are clearly fake and only exist in these test fixtures.
"""

import pytest

from vault.crypto import (
    derive_key,
    encrypt,
    decrypt,
    generate_salt,
    generate_nonce,
    KEY_LENGTH,
    SALT_LENGTH,
    NONCE_LENGTH,
)


# ---------------------------------------------------------------------------
# Salt / Nonce generation
# ---------------------------------------------------------------------------

class TestRandomGeneration:
    def test_salt_length(self):
        salt = generate_salt()
        assert len(salt) == SALT_LENGTH

    def test_salt_is_bytes(self):
        assert isinstance(generate_salt(), bytes)

    def test_two_salts_are_different(self):
        """Salts must be random; equal salts would be a critical failure."""
        salt1 = generate_salt()
        salt2 = generate_salt()
        assert salt1 != salt2

    def test_nonce_length(self):
        nonce = generate_nonce()
        assert len(nonce) == NONCE_LENGTH

    def test_two_nonces_are_different(self):
        assert generate_nonce() != generate_nonce()


# ---------------------------------------------------------------------------
# Key derivation (scrypt)
# ---------------------------------------------------------------------------

class TestKeyDerivation:
    FAKE_PASSWORD = "TestPassword!Only#For$Testing"
    FIXED_SALT = b"\x01" * SALT_LENGTH

    def test_key_is_correct_length(self):
        key = derive_key(self.FAKE_PASSWORD, self.FIXED_SALT)
        assert len(key) == KEY_LENGTH  # 32 bytes for AES-256

    def test_key_is_bytes(self):
        key = derive_key(self.FAKE_PASSWORD, self.FIXED_SALT)
        assert isinstance(key, bytes)

    def test_same_password_and_salt_produce_same_key(self):
        """scrypt must be deterministic for the same inputs."""
        key1 = derive_key(self.FAKE_PASSWORD, self.FIXED_SALT)
        key2 = derive_key(self.FAKE_PASSWORD, self.FIXED_SALT)
        assert key1 == key2

    def test_different_passwords_produce_different_keys(self):
        key1 = derive_key("PasswordAlpha!1", self.FIXED_SALT)
        key2 = derive_key("PasswordBeta!2", self.FIXED_SALT)
        assert key1 != key2

    def test_different_salts_produce_different_keys(self):
        """The salt must meaningfully change the derived key."""
        salt1 = b"\x01" * SALT_LENGTH
        salt2 = b"\x02" * SALT_LENGTH
        key1 = derive_key(self.FAKE_PASSWORD, salt1)
        key2 = derive_key(self.FAKE_PASSWORD, salt2)
        assert key1 != key2

    def test_unicode_password_is_handled(self):
        """Non-ASCII master passwords must not crash key derivation."""
        key = derive_key("PässwörtMitÄÖÜ!99", self.FIXED_SALT)
        assert len(key) == KEY_LENGTH


# ---------------------------------------------------------------------------
# AES-256-GCM encryption / decryption
# ---------------------------------------------------------------------------

class TestEncryptDecrypt:
    FAKE_PASSWORD = "AnotherFakePassword#42"
    SALT = b"\xab" * SALT_LENGTH
    PLAINTEXT = b'[{"id":"1","website":"test.example","username":"user@test","password":"pw","notes":""}]'

    @pytest.fixture
    def key(self):
        return derive_key(self.FAKE_PASSWORD, self.SALT)

    def test_decrypt_round_trip(self, key):
        nonce, ciphertext = encrypt(key, self.PLAINTEXT)
        recovered = decrypt(key, nonce, ciphertext)
        assert recovered == self.PLAINTEXT

    def test_ciphertext_is_different_from_plaintext(self, key):
        nonce, ciphertext = encrypt(key, self.PLAINTEXT)
        assert ciphertext != self.PLAINTEXT

    def test_each_encryption_produces_unique_nonce(self, key):
        nonce1, _ = encrypt(key, self.PLAINTEXT)
        nonce2, _ = encrypt(key, self.PLAINTEXT)
        assert nonce1 != nonce2

    def test_each_encryption_produces_unique_ciphertext(self, key):
        """Different nonces must produce different ciphertexts."""
        _, ct1 = encrypt(key, self.PLAINTEXT)
        _, ct2 = encrypt(key, self.PLAINTEXT)
        assert ct1 != ct2

    def test_wrong_key_cannot_decrypt(self, key):
        nonce, ciphertext = encrypt(key, self.PLAINTEXT)
        wrong_key = derive_key("WrongPassword!99", self.SALT)
        with pytest.raises(ValueError):
            decrypt(wrong_key, nonce, ciphertext)

    def test_tampered_ciphertext_fails_authentication(self, key):
        """GCM authentication tag must catch any modification."""
        nonce, ciphertext = encrypt(key, self.PLAINTEXT)
        # Flip a bit in the ciphertext
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF
        with pytest.raises(ValueError):
            decrypt(key, nonce, bytes(tampered))

    def test_wrong_nonce_fails(self, key):
        nonce, ciphertext = encrypt(key, self.PLAINTEXT)
        wrong_nonce = bytes(b ^ 0xFF for b in nonce)
        with pytest.raises(ValueError):
            decrypt(key, wrong_nonce, ciphertext)

    def test_empty_plaintext(self, key):
        nonce, ciphertext = encrypt(key, b"")
        assert decrypt(key, nonce, ciphertext) == b""
