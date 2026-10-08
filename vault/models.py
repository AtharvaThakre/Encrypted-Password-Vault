"""
vault/models.py
---------------
Data model for a single password-vault entry.

Uses a plain dataclass so there is no ORM or database dependency.
All serialisation to/from dicts is handled here to keep other modules clean.

SECURITY NOTE: Instances of VaultEntry are kept only in RAM (inside the
decrypted vault list in manager.py).  They are NEVER written to disk in
plaintext.
"""

from __future__ import annotations
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class VaultEntry:
    """
    A single credential record stored inside the encrypted vault.

    Attributes
    ----------
    id : str
        Unique identifier (UUID4) assigned when the entry is created.
    website : str
        Service name or URL (e.g. "GitHub", "https://github.com").
    username : str
        Login username or e-mail address.
    password : str
        The credential password — kept in RAM only, never plaintext on disk.
    notes : str
        Optional free-text notes.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    website: str = ""
    username: str = ""
    password: str = ""
    notes: str = ""

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a plain dict representation (for JSON serialisation)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "VaultEntry":
        """Reconstruct a VaultEntry from a plain dict."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            website=data.get("website", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            notes=data.get("notes", ""),
        )

    def matches_search(self, query: str) -> bool:
        """
        Return True if *query* appears (case-insensitive) in website or
        username.  Search is performed against the in-RAM decrypted data;
        nothing is written to disk.
        """
        q = query.lower()
        return q in self.website.lower() or q in self.username.lower()
