"""
gui/entry_dialog.py  —  add / edit password entry dialog.
Black & white, minimal Tkinter UI.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from vault.models import VaultEntry
from gui.password_generator import PasswordGeneratorDialog


class EntryDialog(tk.Toplevel):
    def __init__(self, parent: tk.Widget, on_save: Callable[[VaultEntry], None],
                 entry: Optional[VaultEntry] = None):
        super().__init__(parent)
        self._on_save = on_save
        self._edit_entry = entry
        self._is_edit = entry is not None

        self.title("Edit Entry" if self._is_edit else "Add Entry")
        self.resizable(False, False)
        self.configure(bg="white")
        self.grab_set()

        self._build_ui()
        if self._is_edit:
            self._populate(entry)
        self._center(parent)

    def _build_ui(self) -> None:
        PX = 24

        tk.Label(self, text="Edit Entry" if self._is_edit else "Add Entry",
                 font=("Courier", 13, "bold"), fg="black", bg="white").pack(pady=(16, 12))

        self._website_var = self._labeled_entry("Website / Service", PX)
        self._username_var = self._labeled_entry("Username / Email", PX)

        # Password row
        tk.Label(self, text="Password", font=("Courier", 10, "bold"),
                 fg="black", bg="white", anchor="w").pack(fill="x", padx=PX)

        pw_row = tk.Frame(self, bg="white")
        pw_row.pack(fill="x", padx=PX, pady=(4, 0))
        pw_row.columnconfigure(0, weight=1)

        self._password_var = tk.StringVar()
        self._pw_entry = tk.Entry(pw_row, textvariable=self._password_var, show="*",
                                   font=("Courier", 11), bg="white", fg="black",
                                   insertbackground="black", relief="solid", bd=1)
        self._pw_entry.grid(row=0, column=0, sticky="ew", ipady=6, padx=(0, 4))

        self._show_pw = False
        tk.Button(pw_row, text="show", command=self._toggle_pw,
                  font=("Courier", 9), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2").grid(row=0, column=1, ipady=6, padx=(0, 4))

        tk.Button(pw_row, text="Generate", command=self._open_generator,
                  font=("Courier", 9), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2").grid(row=0, column=2, ipady=6)

        # Notes
        tk.Label(self, text="Notes (optional)", font=("Courier", 10, "bold"),
                 fg="black", bg="white", anchor="w").pack(fill="x", padx=PX, pady=(12, 0))

        self._notes_text = tk.Text(self, font=("Courier", 10), bg="white", fg="black",
                                    insertbackground="black", relief="solid", bd=1,
                                    height=3, wrap="word")
        self._notes_text.pack(fill="x", padx=PX, pady=(4, 0))

        # Buttons
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(fill="x", padx=PX, pady=16)

        tk.Button(btn_frame, text="Save", command=self._on_save_click,
                  font=("Courier", 10, "bold"), bg="black", fg="white",
                  activebackground="#333333", activeforeground="white",
                  relief="flat", cursor="hand2", padx=16, pady=7).pack(side="left")

        tk.Button(btn_frame, text="Cancel", command=self.destroy,
                  font=("Courier", 10), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2", padx=16, pady=7).pack(side="right")

    def _labeled_entry(self, label: str, pad_x: int) -> tk.StringVar:
        tk.Label(self, text=label, font=("Courier", 10, "bold"),
                 fg="black", bg="white", anchor="w").pack(fill="x", padx=pad_x, pady=(10, 0))
        var = tk.StringVar()
        tk.Entry(self, textvariable=var, font=("Courier", 11),
                 bg="white", fg="black", insertbackground="black",
                 relief="solid", bd=1).pack(fill="x", padx=pad_x, pady=(4, 0), ipady=6)
        return var

    def _toggle_pw(self) -> None:
        self._show_pw = not self._show_pw
        self._pw_entry.config(show="" if self._show_pw else "*")

    def _open_generator(self) -> None:
        PasswordGeneratorDialog(self, on_use=self._on_generated_password)

    def _on_generated_password(self, password: str) -> None:
        self._password_var.set(password)
        self._pw_entry.config(show="")
        self._show_pw = True

    def _populate(self, entry: VaultEntry) -> None:
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
            messagebox.showwarning("Missing Field", "Website is required.", parent=self)
            return
        if not username:
            messagebox.showwarning("Missing Field", "Username is required.", parent=self)
            return
        if not password:
            messagebox.showwarning("Missing Field", "Password is required.", parent=self)
            return

        if self._is_edit:
            new_entry = VaultEntry(id=self._edit_entry.id, website=website,
                                   username=username, password=password, notes=notes)
        else:
            new_entry = VaultEntry(website=website, username=username,
                                   password=password, notes=notes)

        self._on_save(new_entry)
        self.destroy()

    def _center(self, parent: tk.Widget) -> None:
        self.update_idletasks()
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - self.winfo_width() // 2}+{py - self.winfo_height() // 2}")
