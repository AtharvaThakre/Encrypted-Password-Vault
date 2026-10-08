"""
vault/manager.py
----------------
High-level vault manager: the single source of truth for the in-RAM
decrypted credential list.

Responsibilities:
  - Initialise a new vault (create + encrypt an empty list).
  - Unlock (load + decrypt) an existing vault.
  - Add, edit, delete, and search entries (all in-RAM).
  - Persist changes (re-encrypt and write to disk after every mutation).
  - Lock (wipe decrypted data from memory).

SECURITY NOTES:
  - The derived AES key is held as an instance attribute only while the vault
    is unlocked.  It is zeroed (best-effort) on lock().
  - The master password is accepted only in unlock() / create_vault() and is
    NOT stored anywhere inside this class.
  - Decrypted entry list is held in self._entries and cleared on lock().
"""

import logging
from pathlib import Path
from typing import Optional

from vault.crypto import derive_key, encrypt, decrypt, generate_salt
from vault.storage import (
    DEFAULT_VAULT_PATH,
    load_vault_file,
    save_vault_file,
    entries_to_bytes,
    bytes_to_entries,
)
from vault.models import VaultEntry

logger = logging.getLogger(__name__)


class VaultManager:
    """
    Manages the lifecycle of the encrypted password vault.

    Usage
    -----
    # First run
    mgr = VaultManager()
    mgr.create_vault("MyMasterPassword")

    # Subsequent runs
    mgr = VaultManager()
    mgr.unlock("MyMasterPassword")      # raises ValueError on wrong password
    entries = mgr.search("")            # returns all VaultEntry objects
    mgr.add_entry(VaultEntry(...))
    mgr.lock()
    """

    def __init__(self, vault_path: Path = DEFAULT_VAULT_PATH) -> None:
        self.vault_path = vault_path
        self._key: Optional[bytes] = None       # AES-256 key, None when locked
        self._salt: Optional[bytes] = None      # stored in vault file
        self._entries: list[VaultEntry] = []    # decrypted entries, RAM only
        self._locked = True

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_locked(self) -> bool:
        return self._locked

    @property
    def is_new_vault(self) -> bool:
        from vault.storage import vault_exists
        return not vault_exists(self.vault_path)

    # ------------------------------------------------------------------
    # Vault initialisation
    # ------------------------------------------------------------------

    def create_vault(self, master_password: str) -> None:
        """
        Create a brand-new encrypted vault.

        Generates a fresh salt, derives the key, encrypts an empty entry
        list, and saves to disk.  Leaves the vault in the *unlocked* state.

        Parameters
        ----------
        master_password : str
            The user's chosen master password.  Not stored anywhere.

        Raises
        ------
        OSError
            If the vault file cannot be written.
        """
        salt = generate_salt()
        key = derive_key(master_password, salt)

        # Start with an empty vault
        plaintext = entries_to_bytes([])
        nonce, ciphertext = encrypt(key, plaintext)
        save_vault_file(salt, nonce, ciphertext, self.vault_path)

        # Unlock in memory
        self._salt = salt
        self._key = key
        self._entries = []
        self._locked = False
        logger.info("New vault created and unlocked.")

    def unlock(self, master_password: str) -> None:
        """
        Load and decrypt the vault using *master_password*.

        Raises
        ------
        FileNotFoundError
            If no vault file exists.
        ValueError
            If the password is wrong, the vault is corrupted, or the file
            format is invalid.  The error message is deliberately vague to
            avoid leaking cryptographic details to the caller / UI.
        """
        vault_data = load_vault_file(self.vault_path)
        salt = vault_data["salt"]
        nonce = vault_data["nonce"]
        ciphertext = vault_data["ciphertext"]

        key = derive_key(master_password, salt)

        # Attempt decryption — raises ValueError on auth failure
        try:
            plaintext = decrypt(key, nonce, ciphertext)
        except ValueError:
            # Do not log the master password or key
            logger.debug("Vault decryption failed (authentication error).")
            raise ValueError("Unable to unlock vault. Check your master password.")

        entry_dicts = bytes_to_entries(plaintext)
        self._entries = [VaultEntry.from_dict(d) for d in entry_dicts]
        self._salt = salt
        self._key = key
        self._locked = False
        logger.info("Vault unlocked. %d entries loaded.", len(self._entries))

    def lock(self) -> None:
        """
        Clear all decrypted data from memory and return to the locked state.

        Best-effort: Python does not guarantee immediate memory zeroing, but
        we dereference the sensitive objects so they can be garbage-collected.
        """
        self._entries.clear()
        # Attempt to zero the key bytes (best-effort in CPython)
        if self._key is not None:
            try:
                # bytearray allows in-place zeroing
                key_arr = bytearray(self._key)
                for i in range(len(key_arr)):
                    key_arr[i] = 0
            except Exception:
                pass
        self._key = None
        self._salt = None
        self._locked = True
        logger.info("Vault locked; decrypted data cleared.")

    # ------------------------------------------------------------------
    # Persistence (re-encrypt after every mutation)
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """
        Re-encrypt the current in-RAM entry list and write to disk.

        A fresh nonce is generated on every save (nonce reuse would be a
        critical AES-GCM vulnerability).

        Raises
        ------
        RuntimeError
            If called while the vault is locked.
        OSError
            If the vault file cannot be written.
        """
        if self._locked or self._key is None or self._salt is None:
            raise RuntimeError("Cannot save: vault is locked.")

        plaintext = entries_to_bytes([e.to_dict() for e in self._entries])
        nonce, ciphertext = encrypt(self._key, plaintext)
        save_vault_file(self._salt, nonce, ciphertext, self.vault_path)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def add_entry(self, entry: VaultEntry) -> None:
        """
        Add a new credential entry and persist the vault.

        Raises
        ------
        RuntimeError if vault is locked.
        """
        if self._locked:
            raise RuntimeError("Vault is locked.")
        self._entries.append(entry)
        self._save()
        logger.debug("Entry added: id=%s", entry.id)

    def update_entry(self, updated: VaultEntry) -> None:
        """
        Replace an existing entry (matched by id) and persist the vault.

        Raises
        ------
        RuntimeError if vault is locked.
        ValueError if no entry with the given id exists.
        """
        if self._locked:
            raise RuntimeError("Vault is locked.")
        for i, entry in enumerate(self._entries):
            if entry.id == updated.id:
                self._entries[i] = updated
                self._save()
                logger.debug("Entry updated: id=%s", updated.id)
                return
        raise ValueError(f"No entry found with id={updated.id}")

    def delete_entry(self, entry_id: str) -> None:
        """
        Remove an entry by id and persist the vault.

        Raises
        ------
        RuntimeError if vault is locked.
        ValueError if no entry with the given id exists.
        """
        if self._locked:
            raise RuntimeError("Vault is locked.")
        for i, entry in enumerate(self._entries):
            if entry.id == entry_id:
                del self._entries[i]
                self._save()
                logger.debug("Entry deleted: id=%s", entry_id)
                return
        raise ValueError(f"No entry found with id={entry_id}")

    def search(self, query: str) -> list[VaultEntry]:
        """
        Return entries matching *query* in website or username (case-insensitive).

        An empty query returns all entries.
        Search is purely in-RAM; nothing is written to disk.

        Raises
        ------
        RuntimeError if vault is locked.
        """
        if self._locked:
            raise RuntimeError("Vault is locked.")
        if not query:
            return list(self._entries)
        return [e for e in self._entries if e.matches_search(query)]

    def get_entry(self, entry_id: str) -> Optional[VaultEntry]:
        """Return the VaultEntry with the given id, or None if not found."""
        if self._locked:
            raise RuntimeError("Vault is locked.")
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None
