"""
utils/clipboard.py
------------------
Secure clipboard helpers:
  - Copy a password to the system clipboard.
  - Schedule automatic clearing after 30 seconds.
  - Only clear if the clipboard still contains the password we copied
    (to avoid wiping the user's own data).

Uses pyperclip for cross-platform clipboard access and Python's threading
module for the background timer.

SECURITY NOTE: The clipboard is a shared system resource.  We make a
best-effort attempt to clear the password after the timeout, but
other applications (or the OS) could still read it during those 30 seconds.
Users should be advised to treat the clipboard as transient.
"""

import logging
import threading
import time
from typing import Optional

import pyperclip

logger = logging.getLogger(__name__)

# How long (seconds) before the clipboard is automatically cleared.
CLIPBOARD_CLEAR_DELAY = 30


class ClipboardManager:
    """
    Manages secure, auto-expiring clipboard operations.

    Only one clipboard timer is active at a time.  Copying a new password
    cancels the previous timer so there is no race between two timers.

    Usage
    -----
    cb = ClipboardManager()
    cb.copy_password("MySecret", on_cleared=lambda: print("Clipboard cleared"))
    """

    def __init__(self) -> None:
        self._timer: Optional[threading.Timer] = None
        self._current_password: Optional[str] = None
        self._lock = threading.Lock()

    def copy_password(
        self,
        password: str,
        on_cleared: Optional[callable] = None,
        delay: int = CLIPBOARD_CLEAR_DELAY,
    ) -> None:
        """
        Copy *password* to the clipboard and schedule auto-clearing.

        Parameters
        ----------
        password : str
            The password to copy.  Stored only in RAM, not logged.
        on_cleared : callable, optional
            Called (with no arguments) on the main thread after the clipboard
            is cleared.  Use this to update a status label in the GUI.
            Note: since the timer runs in a background thread, the caller is
            responsible for thread-safe UI updates (e.g. use Tk.after_idle).
        delay : int
            Seconds before auto-clear.  Defaults to CLIPBOARD_CLEAR_DELAY (30).

        Raises
        ------
        Exception
            If pyperclip cannot access the clipboard (e.g. no display).
            The caller should catch and show a user-friendly error.
        """
        with self._lock:
            # Cancel any existing timer
            self._cancel_timer()

            try:
                pyperclip.copy(password)
            except Exception as exc:
                logger.error("Failed to copy to clipboard: %s", type(exc).__name__)
                raise

            # Remember what we copied so we can compare later
            self._current_password = password

            # Schedule clearing
            self._timer = threading.Timer(
                delay, self._clear_if_unchanged, args=(password, on_cleared)
            )
            self._timer.daemon = True
            self._timer.start()
            logger.debug("Password copied; clipboard will be cleared in %ds.", delay)

    def _clear_if_unchanged(
        self, original_password: str, on_cleared: Optional[callable]
    ) -> None:
        """
        Clear the clipboard only if it still contains *original_password*.

        This prevents us from wiping data the user copied themselves after
        our password was placed in the clipboard.
        """
        with self._lock:
            try:
                current = pyperclip.paste()
                if current == original_password:
                    pyperclip.copy("")
                    logger.debug("Clipboard cleared automatically after timeout.")
                else:
                    logger.debug(
                        "Clipboard content changed by user; skipping auto-clear."
                    )
                self._current_password = None
                self._timer = None
            except Exception as exc:
                logger.error(
                    "Error during clipboard auto-clear: %s", type(exc).__name__
                )

        if on_cleared is not None:
            try:
                on_cleared()
            except Exception as exc:
                logger.error("on_cleared callback raised: %s", type(exc).__name__)

    def _cancel_timer(self) -> None:
        """Cancel the current timer, if any.  Must be called with self._lock held."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
            self._current_password = None

    def cancel(self) -> None:
        """Manually cancel the clipboard-clear timer (e.g. when locking the vault)."""
        with self._lock:
            self._cancel_timer()
            logger.debug("Clipboard auto-clear timer cancelled.")
