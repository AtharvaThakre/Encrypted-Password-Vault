"""
gui/password_generator.py  —  secure password generator dialog.
Black & white, minimal Tkinter UI.
Uses secrets module only — never random.
"""

import secrets
import string
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional


class PasswordGeneratorDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, on_use: Callable[[str], None]):
        super().__init__(parent)
        self._on_use = on_use
        self._generated: Optional[str] = None

        self.title("Password Generator")
        self.resizable(False, False)
        self.configure(bg="white")
        self.grab_set()

        self._build_ui()
        self._generate()
        self._center(parent)

    def _build_ui(self) -> None:
        PAD = {"padx": 20, "pady": 5}

        tk.Label(self, text="Password Generator", font=("Courier", 13, "bold"),
                 fg="black", bg="white").pack(pady=(16, 12))

        # Length
        length_frame = tk.Frame(self, bg="white")
        length_frame.pack(fill="x", **PAD)

        tk.Label(length_frame, text="Length:", font=("Courier", 10),
                 fg="black", bg="white", width=10, anchor="w").pack(side="left")

        self._length_var = tk.IntVar(value=20)
        self._length_label = tk.Label(length_frame, text="20",
                                       font=("Courier", 10, "bold"),
                                       fg="black", bg="white", width=3)
        self._length_label.pack(side="right")

        tk.Scale(length_frame, from_=8, to=64, orient="horizontal",
                 variable=self._length_var, command=self._on_length_change,
                 bg="white", fg="black", highlightthickness=0,
                 troughcolor="#cccccc", length=200, showvalue=False).pack(
            side="left", fill="x", expand=True, padx=(0, 6))

        # Checkboxes
        checks_frame = tk.Frame(self, bg="white")
        checks_frame.pack(fill="x", padx=20, pady=4)

        self._use_upper = tk.BooleanVar(value=True)
        self._use_lower = tk.BooleanVar(value=True)
        self._use_digits = tk.BooleanVar(value=True)
        self._use_symbols = tk.BooleanVar(value=True)

        ck = dict(font=("Courier", 10), fg="black", bg="white",
                  activebackground="white", selectcolor="white", cursor="hand2")

        for text, var in [
            ("Uppercase (A-Z)", self._use_upper),
            ("Lowercase (a-z)", self._use_lower),
            ("Numbers  (0-9)", self._use_digits),
            ("Symbols  (!@#)", self._use_symbols),
        ]:
            tk.Checkbutton(checks_frame, text=text, variable=var, **ck).pack(anchor="w")

        # Separator
        tk.Frame(self, bg="black", height=1).pack(fill="x", padx=20, pady=10)

        tk.Label(self, text="Generated:", font=("Courier", 10, "bold"),
                 fg="black", bg="white").pack(anchor="w", padx=20)

        self._password_var = tk.StringVar()
        tk.Entry(self, textvariable=self._password_var,
                 font=("Courier", 12), bg="white", fg="black",
                 insertbackground="black", relief="solid", bd=1,
                 state="readonly").pack(fill="x", padx=20, pady=(4, 0), ipady=6)

        # Buttons
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill="x", padx=20, pady=16)

        bs = dict(font=("Courier", 10), relief="solid", bd=1,
                  cursor="hand2", padx=12, pady=6)

        tk.Button(btn_frame, text="Generate", command=self._generate,
                  bg="white", fg="black", **bs).pack(side="left", padx=(0, 6))

        tk.Button(btn_frame, text="Use Password", command=self._use_password,
                  bg="black", fg="white", activebackground="#333333",
                  activeforeground="white", relief="flat", cursor="hand2",
                  font=("Courier", 10), padx=12, pady=6).pack(side="left")

        tk.Button(btn_frame, text="Cancel", command=self.destroy,
                  bg="white", fg="black", **bs).pack(side="right")

    def _on_length_change(self, value: str) -> None:
        self._length_label.config(text=value)

    def _build_charset(self) -> str:
        charset = ""
        if self._use_upper.get():
            charset += string.ascii_uppercase
        if self._use_lower.get():
            charset += string.ascii_lowercase
        if self._use_digits.get():
            charset += string.digits
        if self._use_symbols.get():
            charset += string.punctuation
        return charset

    def _generate(self) -> None:
        charset = self._build_charset()
        if not charset:
            messagebox.showwarning("No Characters", "Select at least one character type.", parent=self)
            return
        length = self._length_var.get()
        guaranteed = []
        if self._use_upper.get():
            guaranteed.append(secrets.choice(string.ascii_uppercase))
        if self._use_lower.get():
            guaranteed.append(secrets.choice(string.ascii_lowercase))
        if self._use_digits.get():
            guaranteed.append(secrets.choice(string.digits))
        if self._use_symbols.get():
            guaranteed.append(secrets.choice(string.punctuation))
        rest = [secrets.choice(charset) for _ in range(max(0, length - len(guaranteed)))]
        combined = guaranteed + rest
        for i in range(len(combined) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            combined[i], combined[j] = combined[j], combined[i]
        self._generated = "".join(combined)
        self._password_var.set(self._generated)

    def _use_password(self) -> None:
        if not self._generated:
            self._generate()
        if self._generated:
            self._on_use(self._generated)
            self.destroy()

    def _center(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width() // 2}+{py - self.winfo_height() // 2}")
