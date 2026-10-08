"""
gui/main_window.py  —  main vault management window.
Black & white, minimal Tkinter UI.

Scroll behaviour:
  - The entry list uses a Canvas + inner Frame.
  - Mouse-wheel scrolling is bound ONLY to the canvas itself
    (not bind_all), so it only triggers when the pointer is over
    the list area.
  - The scrollbar is shown only when content overflows the canvas height.
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

AUTO_LOCK_SECONDS = 5 * 60


class MainWindow(tk.Frame):
    def __init__(self, parent: tk.Widget, vault: VaultManager,
                 on_lock: Callable[[], None]):
        super().__init__(parent, bg="white")
        self._vault = vault
        self._on_lock = on_lock
        self._clipboard = ClipboardManager()
        self._auto_lock_job: Optional[str] = None
        self._clipboard_status_job: Optional[str] = None
        self._clipboard_seconds_left: int = 0

        self._build_ui()
        self._refresh_entries()
        self._reset_auto_lock()

        parent.bind_all("<Key>", self._on_activity, add="+")
        parent.bind_all("<Button>", self._on_activity, add="+")

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)   # entry list expands

        # ── Header ─────────────────────────────────────────────────────
        header = tk.Frame(self, bg="white")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        tk.Label(header, text="Password Vault", font=("Courier", 14, "bold"),
                 fg="black", bg="white").grid(row=0, column=0, sticky="w",
                                              padx=12, pady=10)

        tk.Button(header, text="Lock", command=self._lock,
                  font=("Courier", 10), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2",
                  padx=10, pady=4).grid(row=0, column=1, padx=12, pady=8)

        tk.Frame(self, bg="black", height=1).grid(row=1, column=0, sticky="ew")

        # ── Search ─────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg="white")
        search_frame.grid(row=1, column=0, sticky="ew")
        search_frame.columnconfigure(1, weight=1)

        tk.Label(search_frame, text="Search:", font=("Courier", 10),
                 fg="black", bg="white").grid(row=0, column=0, padx=(12, 4), pady=8)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        tk.Entry(search_frame, textvariable=self._search_var,
                 font=("Courier", 11), bg="white", fg="black",
                 insertbackground="black", relief="solid", bd=1).grid(
            row=0, column=1, sticky="ew", ipady=5, padx=(0, 12), pady=8)

        tk.Frame(self, bg="black", height=1).grid(row=2, column=0, sticky="ew")

        # ── Scrollable entry list ───────────────────────────────────────
        list_outer = tk.Frame(self, bg="white")
        list_outer.grid(row=3, column=0, sticky="nsew")
        list_outer.columnconfigure(0, weight=1)
        list_outer.rowconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._canvas = tk.Canvas(list_outer, bg="white", highlightthickness=0)
        self._scrollbar = tk.Scrollbar(list_outer, orient="vertical",
                                        command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_yscroll_update)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        # Scrollbar column exists but starts hidden; shown when needed
        list_outer.columnconfigure(1, minsize=0)

        self._entries_frame = tk.Frame(self._canvas, bg="white")
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._entries_frame, anchor="nw")

        self._entries_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse-wheel: bound only to the canvas widget (not bind_all)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", self._on_mousewheel)   # Linux scroll up
        self._canvas.bind("<Button-5>", self._on_mousewheel)   # Linux scroll down

        # ── Separator ──────────────────────────────────────────────────
        tk.Frame(self, bg="black", height=1).grid(row=4, column=0, sticky="ew")

        # ── Footer ─────────────────────────────────────────────────────
        footer = tk.Frame(self, bg="white")
        footer.grid(row=5, column=0, sticky="ew")

        tk.Button(footer, text="+ Add Password", command=self._open_add_dialog,
                  font=("Courier", 11, "bold"), bg="black", fg="white",
                  activebackground="#333333", activeforeground="white",
                  relief="flat", cursor="hand2", padx=14, pady=8).pack(
            side="left", padx=12, pady=8)

        # ── Status bar ─────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self._status_var, font=("Courier", 9),
                 fg="black", bg="white", anchor="w").grid(
            row=6, column=0, sticky="ew", padx=12, pady=(0, 4))

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

    def _on_yscroll_update(self, first: str, last: str) -> None:
        """Show or hide the scrollbar depending on whether content overflows."""
        first_f, last_f = float(first), float(last)
        if first_f <= 0.0 and last_f >= 1.0:
            # All content fits — hide scrollbar
            self._scrollbar.grid_remove()
        else:
            # Content overflows — show scrollbar
            self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._scrollbar.set(first, last)

    def _on_frame_configure(self, event=None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event=None) -> None:
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        """Scroll only when there is overflow."""
        # Check if scrollbar is visible (i.e. content overflows)
        first, last = self._scrollbar.get()
        if first <= 0.0 and last >= 1.0:
            return  # nothing to scroll
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ------------------------------------------------------------------
    # Entry list rendering
    # ------------------------------------------------------------------

    def _refresh_entries(self, query: str = "") -> None:
        for widget in self._entries_frame.winfo_children():
            widget.destroy()

        entries = self._vault.search(query)

        if not entries:
            msg = "No results found." if query else "No passwords saved.\nClick '+ Add Password' to start."
            tk.Label(self._entries_frame, text=msg, font=("Courier", 10),
                     fg="#555555", bg="white", justify="center").pack(pady=30)
            return

        for i, entry in enumerate(entries):
            self._build_entry_row(entry, i)

    def _build_entry_row(self, entry: VaultEntry, index: int) -> None:
        bg = "#f5f5f5" if index % 2 == 0 else "white"

        row = tk.Frame(self._entries_frame, bg=bg)
        row.pack(fill="x")

        # Info
        info = tk.Frame(row, bg=bg)
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        tk.Label(info, text=entry.website or "(no website)",
                 font=("Courier", 11, "bold"), fg="black", bg=bg,
                 anchor="w").pack(anchor="w")

        tk.Label(info, text=entry.username or "(no username)",
                 font=("Courier", 10), fg="#444444", bg=bg,
                 anchor="w").pack(anchor="w")

        if entry.notes:
            preview = entry.notes[:55] + ("..." if len(entry.notes) > 55 else "")
            tk.Label(info, text=preview, font=("Courier", 9, "italic"),
                     fg="#777777", bg=bg, anchor="w").pack(anchor="w")

        # Buttons
        btns = tk.Frame(row, bg=bg)
        btns.pack(side="right", padx=8, pady=8)

        bs = dict(font=("Courier", 9), bg="white", fg="black",
                  relief="solid", bd=1, cursor="hand2", padx=8, pady=4)

        tk.Button(btns, text="Copy",
                  command=lambda e=entry: self._copy_password(e), **bs).pack(
            side="left", padx=2)
        tk.Button(btns, text="Edit",
                  command=lambda e=entry: self._open_edit_dialog(e), **bs).pack(
            side="left", padx=2)
        tk.Button(btns, text="Delete",
                  command=lambda e=entry: self._delete_entry(e), **bs).pack(
            side="left", padx=2)

        # Thin divider
        tk.Frame(self._entries_frame, bg="#dddddd", height=1).pack(fill="x")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_search(self, *_) -> None:
        self._refresh_entries(self._search_var.get().strip())
        self._reset_auto_lock()

    def _open_add_dialog(self) -> None:
        self._reset_auto_lock()
        EntryDialog(self, on_save=self._on_entry_saved)

    def _open_edit_dialog(self, entry: VaultEntry) -> None:
        self._reset_auto_lock()
        EntryDialog(self, on_save=self._on_entry_saved, entry=entry)

    def _on_entry_saved(self, entry: VaultEntry) -> None:
        try:
            if self._vault.get_entry(entry.id) is not None:
                self._vault.update_entry(entry)
                self._set_status("Entry updated.")
            else:
                self._vault.add_entry(entry)
                self._set_status("Password added.")
        except Exception:
            logger.exception("Failed to save entry.")
            messagebox.showerror("Save Error", "Failed to save. Please try again.", parent=self)
            return
        self._refresh_entries(self._search_var.get().strip())

    def _delete_entry(self, entry: VaultEntry) -> None:
        self._reset_auto_lock()
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete entry for:\n  {entry.website}\n  {entry.username}\n\nThis cannot be undone.",
            icon="warning", parent=self
        ):
            return
        try:
            self._vault.delete_entry(entry.id)
            self._set_status("Entry deleted.")
        except Exception:
            logger.exception("Failed to delete entry.")
            messagebox.showerror("Delete Error", "Failed to delete.", parent=self)
            return
        self._refresh_entries(self._search_var.get().strip())

    def _copy_password(self, entry: VaultEntry) -> None:
        self._reset_auto_lock()
        try:
            self._clipboard.copy_password(
                entry.password, on_cleared=self._on_clipboard_cleared)
        except Exception:
            logger.error("Clipboard error")
            messagebox.showerror("Clipboard Error", "Unable to copy to clipboard.", parent=self)
            return
        self._clipboard_seconds_left = 30
        self._update_clipboard_countdown()

    def _update_clipboard_countdown(self) -> None:
        if self._clipboard_seconds_left > 0:
            self._set_status(
                f"Password copied. Clipboard clears in {self._clipboard_seconds_left}s.")
            self._clipboard_seconds_left -= 1
            self._clipboard_status_job = self.after(1000, self._update_clipboard_countdown)
        else:
            self._set_status("Clipboard cleared.")

    def _on_clipboard_cleared(self) -> None:
        self.after_idle(lambda: self._set_status("Clipboard cleared automatically."))

    def _lock(self) -> None:
        self._clipboard.cancel()
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
            self._auto_lock_job = None
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
        self._reset_auto_lock()

    def _reset_auto_lock(self) -> None:
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
        self._auto_lock_job = self.after(
            AUTO_LOCK_SECONDS * 1000, self._auto_lock_triggered)

    def _auto_lock_triggered(self) -> None:
        logger.info("Auto-lock: inactivity timeout.")
        self._lock()

    def destroy(self) -> None:
        self._clipboard.cancel()
        if self._auto_lock_job:
            self.after_cancel(self._auto_lock_job)
        if self._clipboard_status_job:
            self.after_cancel(self._clipboard_status_job)
        super().destroy()
