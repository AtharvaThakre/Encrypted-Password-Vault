"""
gui/entry_dialog.py
-------------------
Add / Edit password entry dialog (Toplevel modal window).

Fields:
  - Website / Service
  - Username / Email
  - Password (masked, with show/hide toggle and password generator)
  - Notes (multi-line)

On Save: calls on_save(VaultEntry) with the completed entry.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from vault.models import VaultEntry
from gui.password_generator import PasswordGeneratorDialog


class EntryDialog(tk.Toplevel):
    """
    Modal dialog for adding or editing a vault entry.

    Parameters
    ----------
    parent : tk.Widget
        Parent window.
    on_save : Callable[[VaultEntry], None]
        Called with the VaultEntry when the user clicks Save.
    entry : VaultEntry, optional
        Pre-populate fields for editing; None means Add mode.
    """

    def __init__(
        self,
        parent: tk.Widget,
        on_save: Callable[[VaultEntry], None],
        entry: Optional[VaultEntry] = None,
    ):
        super().__init__(parent)
        self._on_save = on_save
        self._edit_entry = entry
        self._is_edit = entry is not None

        self.title("Edit Password" if self._is_edit else "Add Password")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self.grab_set()  # modal

        self._build_ui()
        if self._is_edit:
            self._populate(entry)
        self._center(parent)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        PAD_X = 24

        tk.Label(
            self,
            text="Edit Password" if self._is_edit else "Add Password",
            font=("Segoe UI", 14, "bold"),
            fg="#e0e0e0",
            bg="#1a1a2e",
        ).pack(pady=(20, 16))

        # ── Website ────────────────────────────────────────────────────
        self._website_var = self._labeled_entry(
            "Website / Service", PAD_X, placeholder="e.g. GitHub, https://github.com"
        )

        # ── Username ───────────────────────────────────────────────────
        self._username_var = self._labeled_entry(
            "Username / Email", PAD_X, placeholder="e.g. user@example.com"
        )

        # ── Password ───────────────────────────────────────────────────
        tk.Label(
            self,
            text="Password",
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
            anchor="w",
        ).pack(fill="x", padx=PAD_X)

        pw_row = tk.Frame(self, bg="#1a1a2e")
        pw_row.pack(fill="x", padx=PAD_X, pady=(4, 0))
        pw_row.columnconfigure(0, weight=1)

        self._password_var = tk.StringVar()
        self._pw_entry = tk.Entry(
            pw_row,
            textvariable=self._password_var,
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
        tk.Button(
            pw_row,
            text="👁",
            command=self._toggle_pw,
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#9e9e9e",
            relief="flat",
            bd=0,
            cursor="hand2",
        ).grid(row=0, column=1, ipady=8, padx=(0, 4))

        tk.Button(
            pw_row,
            text="Generate",
            command=self._open_generator,
            font=("Segoe UI", 9),
            bg="#0f3460",
            fg="#e0e0e0",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=8,
            pady=8,
        ).grid(row=0, column=2)

        # ── Notes ──────────────────────────────────────────────────────
        tk.Label(
            self,
            text="Notes (optional)",
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
            anchor="w",
        ).pack(fill="x", padx=PAD_X, pady=(14, 0))

        self._notes_text = tk.Text(
            self,
            font=("Segoe UI", 10),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            height=4,
            wrap="word",
        )
        self._notes_text.pack(fill="x", padx=PAD_X, pady=(4, 0))

        # ── Buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=PAD_X, pady=20)

        btn_style = dict(
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=9,
        )

        tk.Button(
            btn_frame,
            text="Save",
            command=self._on_save_click,
            bg="#1b5e20",
            fg="#e0e0e0",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            **btn_style,
        ).pack(side="left")

        tk.Button(
            btn_frame,
            text="Cancel",
            command=self.destroy,
            bg="#37474f",
            fg="#e0e0e0",
            activebackground="#455a64",
            activeforeground="#ffffff",
            **btn_style,
        ).pack(side="right")

    def _labeled_entry(self, label: str, pad_x: int, placeholder: str = "") -> tk.StringVar:
        """Helper: create a label + entry pair and return the StringVar."""
        tk.Label(
            self,
            text=label,
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
            anchor="w",
        ).pack(fill="x", padx=pad_x, pady=(10, 0))

        var = tk.StringVar()
        entry = tk.Entry(
            self,
            textvariable=var,
            font=("Segoe UI", 11),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=0,
        )
        entry.pack(fill="x", padx=pad_x, pady=(4, 0), ipady=8)
        return var

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _toggle_pw(self) -> None:
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "•")

    def _open_generator(self) -> None:
        PasswordGeneratorDialog(self, on_use=self._on_generated_password)

    def _on_generated_password(self, password: str) -> None:
        self._password_var.set(password)
        # Show the generated password briefly so the user can see it
        self._pw_entry.config(show="")
        self._show_pw = True

    def _populate(self, entry: VaultEntry) -> None:
        """Pre-fill fields when editing an existing entry."""
        self._website_var.set(entry.website)
        self._username_var.set(entry.username)
        self._password_var.set(entry.password)
        self._notes_text.insert("1.0", entry.notes)

    def _on_save_click(self) -> None:
        website = self._website_var.get().strip()
        username = self._username_var.get().strip()
        password = self._password_var.get()
        notes = self._notes_text.get("1.0", "end-1c").strip()

        if not website:
            messagebox.showwarning("Missing Field", "Website / Service is required.", parent=self)
            return
        if not username:
            messagebox.showwarning("Missing Field", "Username / Email is required.", parent=self)
            return
        if not password:
            messagebox.showwarning("Missing Field", "Password is required.", parent=self)
            return

        if self._is_edit:
            new_entry = VaultEntry(
                id=self._edit_entry.id,
                website=website,
                username=username,
                password=password,
                notes=notes,
            )
        else:
            new_entry = VaultEntry(
                website=website,
                username=username,
                password=password,
                notes=notes,
            )

        self._on_save(new_entry)
        self.destroy()

    def _center(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")
