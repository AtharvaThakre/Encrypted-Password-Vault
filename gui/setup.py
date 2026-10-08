"""
gui/setup.py  —  first-run vault creation screen.
Black & white, minimal Tkinter UI.
"""

import re
import tkinter as tk
from tkinter import messagebox
from typing import Callable


def _check_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 12:
        return False, "Password must be at least 12 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Must contain at least one digit."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~]", password):
        return False, "Must contain at least one special character."
    return True, ""


class SetupScreen(tk.Frame):
    def __init__(self, parent: tk.Widget, on_vault_created: Callable[[str], None]):
        super().__init__(parent, bg="white")
        self._on_vault_created = on_vault_created
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        tk.Label(self, text="Password Vault", font=("Courier", 18, "bold"),
                 fg="black", bg="white").grid(row=0, column=0, pady=(40, 4))

        tk.Label(self, text="Create a master password to get started",
                 font=("Courier", 10), fg="#555555", bg="white").grid(
            row=1, column=0, pady=(0, 24))

        # --- Master password ---
        tk.Label(self, text="Master Password", font=("Courier", 10, "bold"),
                 fg="black", bg="white", anchor="w").grid(
            row=2, column=0, sticky="ew", padx=60)

        pw_frame = tk.Frame(self, bg="white")
        pw_frame.grid(row=3, column=0, sticky="ew", padx=60, pady=(4, 0))
        pw_frame.columnconfigure(0, weight=1)

        self._pw_var = tk.StringVar()
        self._pw_entry = tk.Entry(pw_frame, textvariable=self._pw_var, show="*",
                                   font=("Courier", 11), bg="white", fg="black",
                                   insertbackground="black",
                                   relief="solid", bd=1)
        self._pw_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 4))

        self._show_pw = False
        tk.Button(pw_frame, text="show", command=self._toggle_pw,
                  font=("Courier", 9), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2").grid(row=0, column=1, ipady=6)

        self._strength_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._strength_var, font=("Courier", 9),
                 fg="black", bg="white", anchor="w").grid(
            row=4, column=0, sticky="ew", padx=60, pady=(2, 0))
        self._pw_var.trace_add("write", self._on_pw_change)

        # --- Confirm password ---
        tk.Label(self, text="Confirm Password", font=("Courier", 10, "bold"),
                 fg="black", bg="white", anchor="w").grid(
            row=5, column=0, sticky="ew", padx=60, pady=(14, 0))

        confirm_frame = tk.Frame(self, bg="white")
        confirm_frame.grid(row=6, column=0, sticky="ew", padx=60, pady=(4, 0))
        confirm_frame.columnconfigure(0, weight=1)

        self._confirm_var = tk.StringVar()
        self._confirm_entry = tk.Entry(confirm_frame, textvariable=self._confirm_var,
                                        show="*", font=("Courier", 11),
                                        bg="white", fg="black",
                                        insertbackground="black",
                                        relief="solid", bd=1)
        self._confirm_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 4))

        self._show_confirm = False
        tk.Button(confirm_frame, text="show", command=self._toggle_confirm,
                  font=("Courier", 9), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2").grid(row=0, column=1, ipady=6)

        # --- Create button ---
        tk.Button(self, text="Create Vault", command=self._on_create,
                  font=("Courier", 11, "bold"), bg="black", fg="white",
                  activebackground="#333333", activeforeground="white",
                  relief="flat", cursor="hand2", padx=20, pady=8).grid(
            row=7, column=0, pady=(28, 40))

        self._pw_entry.bind("<Return>", lambda e: self._confirm_entry.focus())
        self._confirm_entry.bind("<Return>", lambda e: self._on_create())
        self._pw_entry.focus_set()

    def _toggle_pw(self) -> None:
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "*")

    def _toggle_confirm(self) -> None:
        self._show_confirm = not self._show_confirm
        self._confirm_entry.config(show="" if self._show_confirm else "*")

    def _on_pw_change(self, *_) -> None:
        pw = self._pw_var.get()
        if not pw:
            self._strength_var.set("")
            return
        strong, reason = _check_password_strength(pw)
        self._strength_var.set("OK: strong password" if strong else f"Weak: {reason}")

    def _on_create(self) -> None:
        password = self._pw_var.get()
        confirm = self._confirm_var.get()
        if not password:
            messagebox.showwarning("Missing Input", "Enter a master password.", parent=self)
            return
        strong, reason = _check_password_strength(password)
        if not strong:
            messagebox.showwarning("Weak Password", reason, parent=self)
            return
        if password != confirm:
            messagebox.showerror("Mismatch", "Passwords do not match.", parent=self)
            self._pw_var.set("")
            self._confirm_var.set("")
            self._pw_entry.focus_set()
            return
        self._on_vault_created(password)
        password = ""
        confirm = ""
        self._pw_var.set("")
        self._confirm_var.set("")
