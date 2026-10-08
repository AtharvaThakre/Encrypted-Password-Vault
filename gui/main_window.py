"""
gui/main_window.py
------------------
Main application window — shown after successful vault unlock.

Features:
  - Password entry list (scrollable) with Copy / Edit / Delete per entry.
  - Search box (live, in-RAM, no disk writes).
  - Add Password button.
  - Lock button (clears decrypted data, returns to login).
  - Status bar with clipboard countdown.
  - Auto-lock timer (resets on any UI interaction).
"""

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from vault.manager import VaultManager
from vault.models import VaultEntry
from utils.clipboard import ClipboardManager
from gui.entry_dialog import EntryDialog

logger = logging.getLogger(__name__)

# Auto-lock inactivity timeout in seconds (5 minutes)
AUTO_LOCK_SECONDS = 5 * 60


class MainWindow(tk.Frame):
    """
    Main vault management window.

    Parameters
    ----------
    parent : tk.Widget
        The root Tk window.
    vault : VaultManager
        An already-unlocked VaultManager instance.
    on_lock : Callable[[], None]
        Called when the vault is locked (to switch back to login screen).
    """

    def __init__(
        self,
        parent: tk.Widget,
        vault: VaultManager,
        on_lock: Callable[[], None],
    ):
        super().__init__(parent, bg="#1a1a2e")
        self._vault = vault
        self._on_lock = on_lock
        self._clipboard = ClipboardManager()
        self._auto_lock_job: Optional[str] = None  # after() job id
        self._clipboard_status_job: Optional[str] = None
        self._clipboard_seconds_left: int = 0

        self._build_ui()
        self._refresh_entries()
        self._reset_auto_lock()

        # Bind activity events to reset the auto-lock timer
        parent.bind_all("<Key>", self._on_activity, add="+")
        parent.bind_all("<Button>", self._on_activity, add="+")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Header ─────────────────────────────────────────────────────
        header = tk.Frame(self, bg="#0f3460")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text="🔐 Password Vault",
            font=("Segoe UI", 14, "bold"),
            fg="#e0e0e0",
            bg="#0f3460",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=12)

        tk.Button(
            header,
            text="🔒 Lock",
            command=self._lock,
            font=("Segoe UI", 10, "bold"),
            bg="#16213e",
            fg="#ef9a9a",
            activebackground="#1a1a2e",
            activeforeground="#ef5350",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=12,
            pady=6,
        ).grid(row=0, column=1, padx=12, pady=8)

        # ── Search bar ─────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg="#16213e")
        search_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        search_frame.columnconfigure(1, weight=1)

        tk.Label(
            search_frame,
            text="🔍",
            font=("Segoe UI", 11),
            fg="#9e9e9e",
            bg="#16213e",
        ).grid(row=0, column=0, padx=(12, 4), pady=10)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        tk.Entry(
            search_frame,
            textvariable=self._search_var,
            font=("Segoe UI", 11),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=0,
        ).grid(row=0, column=1, sticky="ew", ipady=8, padx=(0, 12))

        # ── Scrollable entry list ───────────────────────────────────────
        list_outer = tk.Frame(self, bg="#1a1a2e")
        list_outer.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        list_outer.columnconfigure(0, weight=1)
        list_outer.rowconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        canvas = tk.Canvas(list_outer, bg="#1a1a2e", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._entries_frame = tk.Frame(canvas, bg="#1a1a2e")
        self._canvas_window = canvas.create_window(
            (0, 0), window=self._entries_frame, anchor="nw"
        )

        self._entries_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda e: canvas.itemconfig(self._canvas_window, width=e.width),
        )
        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        self._canvas = canvas

        # ── Footer: Add button ──────────────────────────────────────────
        footer = tk.Frame(self, bg="#16213e")
        footer.grid(row=3, column=0, sticky="ew")

        tk.Button(
            footer,
            text="＋ Add Password",
            command=self._open_add_dialog,
            font=("Segoe UI", 11, "bold"),
            bg="#0f3460",
            fg="#e0e0e0",
            activebackground="#16213e",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=20,
            pady=10,
        ).pack(side="left", padx=12, pady=10)

        # Auto-lock indicator
        self._autolock_var = tk.StringVar(value=f"Auto-lock: {AUTO_LOCK_SECONDS // 60} min")
        tk.Label(
            footer,
            textvariable=self._autolock_var,
            font=("Segoe UI", 8),
            fg="#546e7a",
            bg="#16213e",
        ).pack(side="right", padx=12)

        # ── Status bar ──────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="")
        self._status_label = tk.Label(
            self,
            textvariable=self._status_var,
            font=("Segoe UI", 9),
            fg="#80cbc4",
            bg="#1a1a2e",
            anchor="w",
        )
        self._status_label.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 6))

    # ------------------------------------------------------------------
    # Entry list rendering
    # ------------------------------------------------------------------

    def _refresh_entries(self, query: str = "") -> None:
        """Re-render the entry list from the in-memory vault."""
        # Clear existing widgets
        for widget in self._entries_frame.winfo_children():
            widget.destroy()

        entries = self._vault.search(query)

        if not entries:
            tk.Label(
                self._entries_frame,
                text="No entries found." if query else "No passwords saved yet.\nClick '+ Add Password' to get started.",
                font=("Segoe UI", 11),
                fg="#546e7a",
                bg="#1a1a2e",
                justify="center",
            ).pack(pady=40)
            return

        for i, entry in enumerate(entries):
            self._build_entry_card(entry, i)

    def _build_entry_card(self, entry: VaultEntry, index: int) -> None:
        """Build a single card widget for a vault entry."""
        bg_color = "#16213e" if index % 2 == 0 else "#1a1a2e"

        card = tk.Frame(
            self._entries_frame,
            bg=bg_color,
            relief="flat",
            bd=0,
        )
        card.pack(fill="x", padx=0, pady=1)
        card.columnconfigure(0, weight=1)

        info_frame = tk.Frame(card, bg=bg_color)
        info_frame.grid(row=0, column=0, sticky="w", padx=16, pady=(10, 2))

        # Website (bold)
        tk.Label(
            info_frame,
            text=entry.website or "(no website)",
            font=("Segoe UI", 11, "bold"),
            fg="#e0e0e0",
            bg=bg_color,
        ).pack(anchor="w")

        # Username
        tk.Label(
            info_frame,
            text=entry.username or "(no username)",
            font=("Segoe UI", 10),
            fg="#9e9e9e",
            bg=bg_color,
        ).pack(anchor="w")

        # Notes preview (if any)
        if entry.notes:
            preview = entry.notes[:60] + ("…" if len(entry.notes) > 60 else "")
            tk.Label(
                info_frame,
                text=preview,
                font=("Segoe UI", 9, "italic"),
                fg="#616161",
                bg=bg_color,
            ).pack(anchor="w")

        # Buttons
        btn_frame = tk.Frame(card, bg=bg_color)
        btn_frame.grid(row=0, column=1, padx=12, pady=8)

        btn_style = dict(
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=5,
        )

        tk.Button(
            btn_frame,
            text="⎘ Copy",
            command=lambda e=entry: self._copy_password(e),
            bg="#0d47a1",
            fg="#e0e0e0",
            activebackground="#1565c0",
            **btn_style,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="✏ Edit",
            command=lambda e=entry: self._open_edit_dialog(e),
            bg="#1565c0",
            fg="#e0e0e0",
            activebackground="#1976d2",
            **btn_style,
        ).pack(side="left", padx=2)

        tk.Button(
            btn_frame,
            text="✕ Delete",
            command=lambda e=entry: self._delete_entry(e),
            bg="#b71c1c",
            fg="#e0e0e0",
            activebackground="#c62828",
            **btn_style,
        ).pack(side="left", padx=2)

        # Separator line
        tk.Frame(self._entries_frame, bg="#0f3460", height=1).pack(fill="x")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_search(self, *_) -> None:
        query = self._search_var.get().strip()
        self._refresh_entries(query)
        self._reset_auto_lock()

    def _open_add_dialog(self) -> None:
        self._reset_auto_lock()
        EntryDialog(self, on_save=self._on_entry_saved)

    def _open_edit_dialog(self, entry: VaultEntry) -> None:
        self._reset_auto_lock()
        EntryDialog(self, on_save=self._on_entry_saved, entry=entry)

    def _on_entry_saved(self, entry: VaultEntry) -> None:
        """Called by EntryDialog after user clicks Save."""
        try:
            if self._vault.get_entry(entry.id) is not None:
                self._vault.update_entry(entry)
                self._set_status("Entry updated and vault saved.")
            else:
                self._vault.add_entry(entry)
                self._set_status("Password added and vault saved.")
        except Exception as exc:
            logger.exception("Failed to save entry.")
            messagebox.showerror(
                "Save Error",
                "Failed to save the entry. Please try again.",
                parent=self,
            )
            return
        self._refresh_entries(self._search_var.get().strip())

    def _delete_entry(self, entry: VaultEntry) -> None:
        self._reset_auto_lock()
        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the entry for:\n\n"
            f"  {entry.website}\n  {entry.username}\n\n"
            "This action cannot be undone.",
            icon="warning",
            parent=self,
        )
        if not confirmed:
            return
        try:
            self._vault.delete_entry(entry.id)
            self._set_status("Entry deleted.")
        except Exception:
            logger.exception("Failed to delete entry.")
            messagebox.showerror(
                "Delete Error", "Failed to delete the entry.", parent=self
            )
            return
        self._refresh_entries(self._search_var.get().strip())

    def _copy_password(self, entry: VaultEntry) -> None:
        """Copy the entry's password to clipboard with auto-clear."""
        self._reset_auto_lock()
        try:
            self._clipboard.copy_password(
                entry.password,
                on_cleared=self._on_clipboard_cleared,
            )
        except Exception as exc:
            logger.error("Clipboard error: %s", type(exc).__name__)
            messagebox.showerror(
                "Clipboard Error",
                "Unable to copy to clipboard.\n"
                "Make sure a clipboard manager is available.",
                parent=self,
            )
            return

        self._clipboard_seconds_left = 30
        self._update_clipboard_countdown()
        logger.debug("Password for '%s' copied to clipboard.", entry.website)

    def _update_clipboard_countdown(self) -> None:
        """Update the status bar countdown every second."""
        if self._clipboard_seconds_left > 0:
            self._set_status(
                f"Password copied to clipboard. "
                f"Clipboard will be cleared in {self._clipboard_seconds_left}s."
            )
            self._clipboard_seconds_left -= 1
            self._clipboard_status_job = self.after(
                1000, self._update_clipboard_countdown
            )
        else:
            # Timer expired; the actual clear is handled by ClipboardManager
            self._set_status("Clipboard cleared.")

    def _on_clipboard_cleared(self) -> None:
        """Called from the background clipboard timer thread."""
        # Schedule UI update on the main thread
        self.after_idle(lambda: self._set_status("Clipboard cleared automatically."))

    def _lock(self) -> None:
        """Lock the vault and return to login screen."""
        self._clipboard.cancel()
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
            self._auto_lock_job = None

        # Unbind activity events
        try:
            self.winfo_toplevel().unbind_all("<Key>")
            self.winfo_toplevel().unbind_all("<Button>")
        except Exception:
            pass

        self._vault.lock()
        self._set_status("")
        self._on_lock()

    def _set_status(self, message: str) -> None:
        self._status_var.set(message)

    # ------------------------------------------------------------------
    # Auto-lock
    # ------------------------------------------------------------------

    def _on_activity(self, event=None) -> None:
        """Reset the auto-lock timer on any user interaction."""
        self._reset_auto_lock()

    def _reset_auto_lock(self) -> None:
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
        self._auto_lock_job = self.after(
            AUTO_LOCK_SECONDS * 1000, self._auto_lock_triggered
        )

    def _auto_lock_triggered(self) -> None:
        logger.info("Auto-lock triggered due to inactivity.")
        self._set_status("")
        self._lock()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def destroy(self) -> None:
        """Clean up timers before destroying the frame."""
        self._clipboard.cancel()
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
        if self._clipboard_status_job:
            self.after_cancel(self._clipboard_status_job)
        super().destroy()
