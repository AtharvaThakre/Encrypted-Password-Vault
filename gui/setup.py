"""
gui/setup.py
------------
Setup screen shown on the very first launch (no vault.enc exists).

Allows the user to:
  1. Choose a master password.
  2. Confirm it.
  3. Create a new encrypted vault.

Password-strength validation:
  - Minimum 12 characters
  - At least one uppercase, one lowercase, one digit, one special character
"""

import logging
import re
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

logger = logging.getLogger(__name__)


def _check_password_strength(password: str) -> tuple[bool, str]:
    """
    Return (is_strong, reason).

    Enforces:
      - Minimum 12 characters
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
      - At least one special character
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        return False, "Password must contain at least one special character."
    return True, ""


class SetupScreen(tk.Frame):
    """
    First-run setup frame embedded in the main application window.

    Parameters
    ----------
    parent : tk.Widget
        The parent container (usually the root Tk window).
    on_vault_created : Callable[[str], None]
        Called with the master password string after the vault is
        successfully created.  The caller (App) then calls
        vault_manager.create_vault() and transitions to the main window.
    """

    def __init__(self, parent: tk.Widget, on_vault_created: Callable[[str], None]):
        super().__init__(parent, bg="#1a1a2e")
        self._on_vault_created = on_vault_created
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
        ).grid(row=0, column=0, pady=(40, 4))

        tk.Label(
            self,
            text="Create your master password",
            font=("Segoe UI", 11),
            fg="#9e9e9e",
            bg="#1a1a2e",
        ).grid(row=1, column=0, pady=(0, 28))

        # ── Password field ─────────────────────────────────────────────
        tk.Label(
            self,
            text="Master Password",
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=60)

        pw_frame = tk.Frame(self, bg="#1a1a2e")
        pw_frame.grid(row=3, column=0, sticky="ew", padx=60, pady=(4, 0))
        pw_frame.columnconfigure(0, weight=1)

        self._pw_var = tk.StringVar()
        self._pw_entry = tk.Entry(
            pw_frame,
            textvariable=self._pw_var,
            show="•",
            font=("Segoe UI", 11),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=0,
        )
        self._pw_entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 4))

        self._show_pw = False
        self._toggle_pw_btn = tk.Button(
            pw_frame,
            text="👁",
            command=self._toggle_pw,
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#9e9e9e",
            relief="flat",
            bd=0,
            cursor="hand2",
        )
        self._toggle_pw_btn.grid(row=0, column=1, ipady=8, padx=(0, 0))

        # Strength indicator
        self._strength_var = tk.StringVar(value="")
        tk.Label(
            self,
            textvariable=self._strength_var,
            font=("Segoe UI", 9),
            fg="#ff7043",
            bg="#1a1a2e",
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=60, pady=(2, 0))
        self._pw_var.trace_add("write", self._on_pw_change)

        # ── Confirm password field ─────────────────────────────────────
        tk.Label(
            self,
            text="Confirm Password",
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
            anchor="w",
        ).grid(row=5, column=0, sticky="ew", padx=60, pady=(18, 0))

        confirm_frame = tk.Frame(self, bg="#1a1a2e")
        confirm_frame.grid(row=6, column=0, sticky="ew", padx=60, pady=(4, 0))
        confirm_frame.columnconfigure(0, weight=1)

        self._confirm_var = tk.StringVar()
        self._confirm_entry = tk.Entry(
            confirm_frame,
            textvariable=self._confirm_var,
            show="•",
            font=("Segoe UI", 11),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=0,
        )
        self._confirm_entry.grid(row=0, column=0, sticky="ew", ipady=8, padx=(0, 4))

        self._show_confirm = False
        self._toggle_confirm_btn = tk.Button(
            confirm_frame,
            text="👁",
            command=self._toggle_confirm,
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#9e9e9e",
            relief="flat",
            bd=0,
            cursor="hand2",
        )
        self._toggle_confirm_btn.grid(row=0, column=1, ipady=8)

        # ── Create Vault button ────────────────────────────────────────
        self._create_btn = tk.Button(
            self,
            text="Create Vault",
            command=self._on_create,
            font=("Segoe UI", 11, "bold"),
            bg="#0f3460",
            fg="#e0e0e0",
            activebackground="#16213e",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=24,
            pady=10,
        )
        self._create_btn.grid(row=7, column=0, pady=(30, 40))

        # Bind Enter key
        self._pw_entry.bind("<Return>", lambda e: self._confirm_entry.focus())
        self._confirm_entry.bind("<Return>", lambda e: self._on_create())

        self._pw_entry.focus_set()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _toggle_pw(self) -> None:
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "•")

    def _toggle_confirm(self) -> None:
        self._show_confirm = not self._show_confirm
        self._confirm_entry.config(show="" if self._show_confirm else "•")

    def _on_pw_change(self, *_) -> None:
        pw = self._pw_var.get()
        if not pw:
            self._strength_var.set("")
            return
        strong, reason = _check_password_strength(pw)
        if strong:
            self._strength_var.set("✔ Strong password")
            # change colour to green
            for widget in self.winfo_children():
                if isinstance(widget, tk.Label) and widget.cget("textvariable") == str(self._strength_var):
                    widget.config(fg="#66bb6a")
        else:
            self._strength_var.set(f"✘ {reason}")

    def _on_create(self) -> None:
        password = self._pw_var.get()
        confirm = self._confirm_var.get()

        if not password:
            messagebox.showwarning("Missing Input", "Please enter a master password.", parent=self)
            return

        strong, reason = _check_password_strength(password)
        if not strong:
            messagebox.showwarning("Weak Password", reason, parent=self)
            return

        if password != confirm:
            messagebox.showerror("Mismatch", "Passwords do not match.", parent=self)
            # Clear both fields for security
            self._pw_var.set("")
            self._confirm_var.set("")
            self._pw_entry.focus_set()
            return

        # Hand off to the app — master password NOT stored here
        self._on_vault_created(password)

        # Zero local references immediately after handoff
        password = ""
        confirm = ""
        self._pw_var.set("")
        self._confirm_var.set("")
