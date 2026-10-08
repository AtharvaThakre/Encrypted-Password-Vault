"""
gui/password_generator.py
--------------------------
Secure password generator dialog.

Uses Python's `secrets` module for cryptographically secure random selection.
The normal `random` module is NOT used.

The dialog is a Toplevel (modal) window that:
  - Lets the user choose length (8–64).
  - Toggle uppercase / lowercase / digits / symbols.
  - Click Generate to create a new password.
  - Click Use Password to return the generated password to the caller.
"""

import secrets
import string
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional


class PasswordGeneratorDialog(tk.Toplevel):
    """
    Modal password-generator dialog.

    Parameters
    ----------
    parent : tk.Widget
        Parent window.
    on_use : Callable[[str], None]
        Called with the generated password when the user clicks Use Password.
    """

    def __init__(self, parent: tk.Widget, on_use: Callable[[str], None]):
        super().__init__(parent)
        self._on_use = on_use
        self._generated: Optional[str] = None

        self.title("Password Generator")
        self.resizable(False, False)
        self.configure(bg="#1a1a2e")
        self.grab_set()  # modal

        self._build_ui()
        self._generate()  # Show an initial password
        self._center(parent)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        PAD = {"padx": 20, "pady": 6}

        tk.Label(
            self,
            text="Password Generator",
            font=("Segoe UI", 14, "bold"),
            fg="#e0e0e0",
            bg="#1a1a2e",
        ).pack(pady=(20, 4))

        tk.Label(
            self,
            text="Uses cryptographically secure randomness (secrets module)",
            font=("Segoe UI", 8),
            fg="#757575",
            bg="#1a1a2e",
        ).pack(pady=(0, 12))

        # ── Length slider ──────────────────────────────────────────────
        length_frame = tk.Frame(self, bg="#1a1a2e")
        length_frame.pack(fill="x", **PAD)

        tk.Label(
            length_frame,
            text="Length:",
            font=("Segoe UI", 10),
            fg="#b0bec5",
            bg="#1a1a2e",
            width=10,
            anchor="w",
        ).pack(side="left")

        self._length_var = tk.IntVar(value=20)
        self._length_label = tk.Label(
            length_frame,
            text="20",
            font=("Segoe UI", 10, "bold"),
            fg="#e0e0e0",
            bg="#1a1a2e",
            width=4,
        )
        self._length_label.pack(side="right")

        tk.Scale(
            length_frame,
            from_=8,
            to=64,
            orient="horizontal",
            variable=self._length_var,
            command=self._on_length_change,
            bg="#16213e",
            fg="#e0e0e0",
            highlightthickness=0,
            troughcolor="#0f3460",
            activebackground="#0f3460",
            length=220,
            showvalue=False,
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        # ── Character-set checkboxes ───────────────────────────────────
        checks_frame = tk.Frame(self, bg="#1a1a2e")
        checks_frame.pack(fill="x", padx=20, pady=4)

        self._use_upper = tk.BooleanVar(value=True)
        self._use_lower = tk.BooleanVar(value=True)
        self._use_digits = tk.BooleanVar(value=True)
        self._use_symbols = tk.BooleanVar(value=True)

        check_style = dict(
            font=("Segoe UI", 10),
            fg="#b0bec5",
            bg="#1a1a2e",
            activebackground="#1a1a2e",
            activeforeground="#e0e0e0",
            selectcolor="#0f3460",
            cursor="hand2",
        )

        for text, var in [
            ("Uppercase (A-Z)", self._use_upper),
            ("Lowercase (a-z)", self._use_lower),
            ("Numbers (0-9)", self._use_digits),
            ("Symbols (!@#…)", self._use_symbols),
        ]:
            tk.Checkbutton(checks_frame, text=text, variable=var, **check_style).pack(
                anchor="w"
            )

        # ── Generated password display ─────────────────────────────────
        sep = tk.Frame(self, bg="#0f3460", height=1)
        sep.pack(fill="x", padx=20, pady=12)

        tk.Label(
            self,
            text="Generated Password:",
            font=("Segoe UI", 10, "bold"),
            fg="#b0bec5",
            bg="#1a1a2e",
        ).pack(anchor="w", padx=20)

        self._password_var = tk.StringVar()
        pw_display = tk.Entry(
            self,
            textvariable=self._password_var,
            font=("Courier New", 12, "bold"),
            bg="#16213e",
            fg="#80cbc4",
            insertbackground="#80cbc4",
            relief="flat",
            state="readonly",
        )
        pw_display.pack(fill="x", padx=20, pady=(4, 0), ipady=8)

        # ── Buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill="x", padx=20, pady=20)

        btn_style = dict(
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=16,
            pady=8,
        )

        tk.Button(
            btn_frame,
            text="↻ Generate",
            command=self._generate,
            bg="#0f3460",
            fg="#e0e0e0",
            activebackground="#16213e",
            activeforeground="#ffffff",
            **btn_style,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_frame,
            text="✔ Use Password",
            command=self._use_password,
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

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------

    def _on_length_change(self, value: str) -> None:
        self._length_label.config(text=value)

    def _build_charset(self) -> str:
        """Build the character pool from selected options."""
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
        """Generate a new password using secrets.choice()."""
        charset = self._build_charset()
        if not charset:
            messagebox.showwarning(
                "No Characters Selected",
                "Please select at least one character type.",
                parent=self,
            )
            return

        length = self._length_var.get()

        # Guarantee at least one character from each selected class
        guaranteed = []
        if self._use_upper.get():
            guaranteed.append(secrets.choice(string.ascii_uppercase))
        if self._use_lower.get():
            guaranteed.append(secrets.choice(string.ascii_lowercase))
        if self._use_digits.get():
            guaranteed.append(secrets.choice(string.digits))
        if self._use_symbols.get():
            guaranteed.append(secrets.choice(string.punctuation))

        remaining_length = max(0, length - len(guaranteed))
        rest = [secrets.choice(charset) for _ in range(remaining_length)]

        # Securely shuffle the combined list
        combined = guaranteed + rest
        # Fisher-Yates shuffle using secrets
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
        pw = parent.winfo_rootx() + parent.winfo_width() // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w = self.winfo_width()
        h = self.winfo_height()
        self.geometry(f"+{pw - w // 2}+{ph - h // 2}")
