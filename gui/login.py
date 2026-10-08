"""
gui/login.py
------------
Unlock screen shown when an existing vault.enc is found.

The user enters their master password to decrypt the vault.
Wrong passwords show a generic error message (no cryptographic details).
"""

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable

logger = logging.getLogger(__name__)


class LoginScreen(tk.Frame):
    """
    Login frame embedded in the main application window.

    Parameters
    ----------
    parent : tk.Widget
        The parent container (root Tk window).
    on_unlock : Callable[[str], None]
        Called with the entered password string when the user clicks Unlock.
        The caller is responsible for calling vault_manager.unlock() and
        handling the ValueError that indicates a wrong password.
    """

    def __init__(self, parent: tk.Widget, on_unlock: Callable[[str], None]):
        super().__init__(parent, bg="#1a1a2e")
        self._on_unlock = on_unlock
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        # ── Title ──────────────────────────────────────────────────────
        tk.Label(
            self,
            text="🔐 Password Vault",
            font=("Segoe UI", 22, "bold"),
            fg="#e0e0e0",
            bg="#1a1a2e",
        ).grid(row=0, column=0, pady=(50, 4))

        tk.Label(
            self,
            text="Enter your master password to unlock",
            font=("Segoe UI", 11),
            fg="#9e9e9e",
            bg="#1a1a2e",
        ).grid(row=1, column=0, pady=(0, 32))

        # ── Password field ─────────────────────────────────────────────
        tk.Label(
            self,
            text="Master Password",
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=70)

        pw_frame = tk.Frame(self, bg="#1a1a2e")
        pw_frame.grid(row=3, column=0, sticky="ew", padx=70, pady=(4, 0))
        pw_frame.columnconfigure(0, weight=1)

        self._pw_var = tk.StringVar()
        self._pw_entry = tk.Entry(
            pw_frame,
            textvariable=self._pw_var,
            show="•",
            font=("Segoe UI", 12),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=0,
        )
        self._pw_entry.grid(row=0, column=0, sticky="ew", ipady=9, padx=(0, 4))

        self._show_pw = False
        tk.Button(
            pw_frame,
            text="👁",
            command=self._toggle_pw,
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#9e9e9e",
            relief="flat",
            bd=0,
            cursor="hand2",
        ).grid(row=0, column=1, ipady=9)

        # ── Error label ────────────────────────────────────────────────
        self._error_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self._error_var,
            font=("Segoe UI", 9),
            fg="#ef5350",
            bg="#1a1a2e",
        ).grid(row=4, column=0, pady=(6, 0))

        # ── Unlock button ──────────────────────────────────────────────
        self._unlock_btn = tk.Button(
            self,
            text="Unlock",
            command=self._on_unlock_click,
            font=("Segoe UI", 11, "bold"),
            bg="#0f3460",
            fg="#e0e0e0",
            activebackground="#16213e",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=28,
            pady=10,
        )
        self._unlock_btn.grid(row=5, column=0, pady=(28, 50))

        self._pw_entry.bind("<Return>", lambda e: self._on_unlock_click())
        self._pw_entry.focus_set()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _toggle_pw(self) -> None:
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "•")

    def _on_unlock_click(self) -> None:
        password = self._pw_var.get()
        if not password:
            self._error_var.set("Please enter your master password.")
            return

        self._error_var.set("")
        self._unlock_btn.config(state="disabled", text="Unlocking…")
        self.update_idletasks()

        # Pass to caller for actual vault unlock
        self._on_unlock(password)

        # Zero local copy
        password = ""
        self._pw_var.set("")
        self._unlock_btn.config(state="normal", text="Unlock")

    def show_error(self, message: str) -> None:
        """Display an error message below the password field."""
        self._error_var.set(message)
