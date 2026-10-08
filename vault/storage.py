"""
vault/storage.py
----------------
Vault file I/O: reading, writing, JSON serialisation, Base64 encoding.

The vault file (vault.enc by default) contains ONLY:
  - version
  - kdf identifier
  - Base64-encoded salt
  - Base64-encoded nonce
  - Base64-encoded ciphertext (with GCM auth tag)

Credentials are embedded inside the ciphertext blob — never in plaintext.

SECURITY NOTE: This module never sees the master password or the derived key.
It only handles opaque bytes (salt, nonce, ciphertext).
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default vault file location (same directory as main.py)
DEFAULT_VAULT_PATH = Path("vault.enc")

VAULT_VERSION = 1
VAULT_KDF = "scrypt"


# ---------------------------------------------------------------------------
# File existence helpers
# ---------------------------------------------------------------------------

def vault_exists(path: Path = DEFAULT_VAULT_PATH) -> bool:
    """Return True if the vault file exists on disk."""
    return path.exists()


# ---------------------------------------------------------------------------
# Read / Write
# ---------------------------------------------------------------------------

def load_vault_file(path: Path = DEFAULT_VAULT_PATH) -> dict:
    """
    Read and parse the vault file.

    Returns a dict with keys: version, kdf, salt, nonce, ciphertext
    (all binary values decoded from Base64 back to bytes).

    Raises
    ------
    FileNotFoundError
        If the vault file does not exist.
    ValueError
        If the file is not valid JSON or is missing required fields.
    """
    if not path.exists():
        raise FileNotFoundError(f"Vault file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except json.JSONDecodeError as exc:
        logger.error("Vault file is not valid JSON.")
        raise ValueError("Vault file is corrupted or invalid.") from exc

    # Validate required fields
    for field in ("version", "kdf", "salt", "nonce", "ciphertext"):
        if field not in raw:
            raise ValueError(f"Vault file is missing required field: '{field}'")

    if raw["version"] != VAULT_VERSION:
        raise ValueError(
            f"Unsupported vault version: {raw['version']}. "
            f"Expected version {VAULT_VERSION}."
        )

    if raw["kdf"] != VAULT_KDF:
        raise ValueError(f"Unsupported KDF: {raw['kdf']}. Expected '{VAULT_KDF}'.")

    try:
        return {
            "version": raw["version"],
            "kdf": raw["kdf"],
            "salt": base64.b64decode(raw["salt"]),
            "nonce": base64.b64decode(raw["nonce"]),
            "ciphertext": base64.b64decode(raw["ciphertext"]),
        }
    except Exception as exc:
        logger.error("Failed to decode Base64 fields in vault file.")
        raise ValueError("Vault file contains invalid Base64 data.") from exc


def save_vault_file(
    salt: bytes,
    nonce: bytes,
    ciphertext: bytes,
    path: Path = DEFAULT_VAULT_PATH,
) -> None:
    """
    Serialise and write the encrypted vault to disk.

    Binary values (salt, nonce, ciphertext) are Base64-encoded so the file
    is valid JSON and can be inspected (but not decoded without the key).

    Parameters
    ----------
    salt : bytes        Per-vault random salt (not secret, needed for key
                        derivation on next unlock).
    nonce : bytes       AES-GCM nonce (not secret, must be unique per save).
    ciphertext : bytes  Encrypted vault blob including GCM auth tag.
    path : Path         Destination file path.

    Raises
    ------
    OSError
        If the file cannot be written (permissions, disk full, etc.).
    """
    payload = {
        "version": VAULT_VERSION,
        "kdf": VAULT_KDF,
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }

    # Write atomically: write to a temp file then rename to avoid partial writes.
    tmp_path = path.with_suffix(".enc.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_path, path)
        logger.debug("Vault saved to %s", path)
    except OSError as exc:
        logger.error("Failed to write vault file: %s", exc)
        # Clean up temp file if it exists
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


# ---------------------------------------------------------------------------
# Vault payload serialisation (entries ↔ bytes)
# ---------------------------------------------------------------------------

def entries_to_bytes(entries: list[dict]) -> bytes:
    """
    Serialise a list of entry dicts to UTF-8 JSON bytes.

    This is the plaintext that AES-GCM encrypts.  It is NEVER written to
    disk in this form.
    """
    return json.dumps(entries, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def bytes_to_entries(data: bytes) -> list[dict]:
    """
    Deserialise UTF-8 JSON bytes back to a list of entry dicts.

    Raises
    ------
    ValueError
        If the bytes are not valid JSON.
    """
    try:
        result = json.loads(data.decode("utf-8"))
        if not isinstance(result, list):
            raise ValueError("Expected a JSON list of entries.")
        return result
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Failed to deserialise vault contents.") from exc
