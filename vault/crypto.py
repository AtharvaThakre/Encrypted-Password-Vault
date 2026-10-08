"""
vault/crypto.py
---------------
All cryptographic operations:
  - scrypt key derivation (master password → 32-byte AES key)
  - AES-256-GCM authenticated encryption / decryption
  - Secure random salt and nonce generation

SECURITY NOTES:
  - Master password is NEVER stored, logged, or written to disk here.
  - Encryption key is NEVER written to disk.
  - A fresh nonce is generated on every encryption call.
  - Using `cryptography` library only — no manual crypto.
"""

import secrets
import logging
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SALT_LENGTH = 32          # bytes  — stored in vault file (not secret)
NONCE_LENGTH = 12         # bytes  — standard for AES-GCM (96-bit)
KEY_LENGTH = 32           # bytes  — AES-256
SCRYPT_N = 2 ** 17        # CPU/memory cost (131072) — OWASP recommended
SCRYPT_R = 8              # block size
SCRYPT_P = 1              # parallelization factor


# ---------------------------------------------------------------------------
# Random material generation
# ---------------------------------------------------------------------------

def generate_salt() -> bytes:
    """Return a cryptographically secure random salt."""
    return secrets.token_bytes(SALT_LENGTH)


def generate_nonce() -> bytes:
    """Return a cryptographically secure random nonce for AES-GCM."""
    return secrets.token_bytes(NONCE_LENGTH)


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def derive_key(master_password: str, salt: bytes) -> bytes:
    """
    Derive a 32-byte AES-256 key from *master_password* and *salt*
    using scrypt (N=2^17, r=8, p=1).

    The same password + same salt always produce the same key, which is
    what lets us verify the master password by attempting decryption.

    Parameters
    ----------
    master_password : str
        The user's master password (UTF-8 encoded before hashing).
    salt : bytes
        The per-vault random salt (stored in vault.enc, not secret).

    Returns
    -------
    bytes
        A 32-byte key suitable for AES-256-GCM.
    """
    kdf = Scrypt(
        salt=salt,
        length=KEY_LENGTH,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        backend=default_backend(),
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return key


# ---------------------------------------------------------------------------
# AES-256-GCM encryption / decryption
# ---------------------------------------------------------------------------

def encrypt(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    """
    Encrypt *plaintext* with AES-256-GCM.

    A unique nonce is generated per call.  The GCM authentication tag is
    appended to the ciphertext by the `cryptography` library.

    Parameters
    ----------
    key : bytes
        32-byte AES-256 key.
    plaintext : bytes
        Data to encrypt (e.g. JSON-encoded vault contents).

    Returns
    -------
    (nonce, ciphertext_with_tag) : tuple[bytes, bytes]
        *nonce* must be stored alongside the ciphertext.
        *ciphertext_with_tag* includes the 16-byte GCM auth tag.
    """
    nonce = generate_nonce()
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext_with_tag


def decrypt(key: bytes, nonce: bytes, ciphertext_with_tag: bytes) -> bytes:
    """
    Decrypt and authenticate AES-256-GCM ciphertext.

    Raises
    ------
    ValueError
        If authentication fails (wrong key, tampered data, or wrong nonce).
        The caller should catch this and show a user-friendly message.
    """
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext
    except Exception:
        # Do NOT propagate internal exception details — they could leak info.
        logger.debug("AES-GCM decryption failed (authentication error).")
        raise ValueError("Decryption failed: incorrect key or corrupted data.")
