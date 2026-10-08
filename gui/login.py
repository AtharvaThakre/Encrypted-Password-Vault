"""
gui/login.py  —  vault unlock screen.
Black & white, minimal Tkinter UI.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable


class LoginScreen(tk.Frame):
    def __init__(self, parent: tk.Widget, on_unlock: Callable[[str], None]):
        super().__init__(parent, bg="white")
        self._on_unlock = on_unlock
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)

        tk.Label(self, text="Password Vault", font=("Courier", 18, "bold"),
                 fg="black", bg="white").grid(row=0, column=0, pady=(50, 4))

        tk.Label(self, text="Enter your master password to unlock",
                 font=("Courier", 10), fg="#555555", bg="white").grid(
            row=1, column=0, pady=(0, 28))

        tk.Label(self, text="Master Password", font=("Courier", 10, "bold"),
                 fg="black", bg="white", anchor="w").grid(
            row=2, column=0, sticky="ew", padx=70)

        pw_frame = tk.Frame(self, bg="white")
        pw_frame.grid(row=3, column=0, sticky="ew", padx=70, pady=(4, 0))
        pw_frame.columnconfigure(0, weight=1)

        self._pw_var = tk.StringVar()
        self._pw_entry = tk.Entry(pw_frame, textvariable=self._pw_var, show="*",
                                   font=("Courier", 12), bg="white", fg="black",
                                   insertbackground="black",
                                   relief="solid", bd=1)
        self._pw_entry.grid(row=0, column=0, sticky="ew", ipady=7, padx=(0, 4))

        self._show_pw = False
        tk.Button(pw_frame, text="show", command=self._toggle_pw,
                  font=("Courier", 9), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2").grid(row=0, column=1, ipady=7)

        self._error_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._error_var, font=("Courier", 9),
                 fg="black", bg="white").grid(row=4, column=0, pady=(6, 0))

        self._unlock_btn = tk.Button(
            self, text="Unlock", command=self._on_unlock_click,
            font=("Courier", 11, "bold"), bg="black", fg="white",
            activebackground="#333333", activeforeground="white",
            relief="flat", cursor="hand2", padx=24, pady=8)
        self._unlock_btn.grid(row=5, column=0, pady=(24, 50))

        self._pw_entry.bind("<Return>", lambda e: self._on_unlock_click())
        self._pw_entry.focus_set()

    def _toggle_pw(self) -> None:
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "*")

    def _on_unlock_click(self) -> None:
        password = self._pw_var.get()
        if not password:
            self._error_var.set("Please enter your master password.")
            return
        self._error_var.set("")
        self._unlock_btn.config(state="disabled", text="Unlocking...")
        self.update_idletasks()
        self._on_unlock(password)
        password = ""
        self._pw_var.set("")
        self._unlock_btn.config(state="normal", text="Unlock")

    def show_error(self, message: str) -> None:
        self._error_var.set(message)
