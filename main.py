"""
main.py
-------
Application entry point.

Responsibilities:
  1. Configure logging (never logs passwords, keys, or vault contents).
  2. Create the root Tk window.
  3. Instantiate VaultManager.
  4. Show the appropriate screen:
       - SetupScreen  → if no vault.enc exists
       - LoginScreen  → if vault.enc exists
       - MainWindow   → after successful unlock/create
  5. Handle screen transitions (setup → main, login → main, main → login).

SECURITY NOTE: The master password travels only as far as vault_manager.create_vault()
or vault_manager.unlock() and is never stored in any application-level attribute.
"""

import logging
import sys
import tkinter as tk
from tkinter import messagebox

from vault.manager import VaultManager
from gui.setup import SetupScreen
from gui.login import LoginScreen
from gui.main_window import MainWindow

# ---------------------------------------------------------------------------
# Logging configuration
# NEVER log: master password, stored passwords, encryption keys, vault content
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Window dimensions
APP_WIDTH = 520
APP_HEIGHT = 640
APP_MIN_WIDTH = 460
APP_MIN_HEIGHT = 400


class App:
    """
    Top-level application controller.

    Owns the Tk root window and the VaultManager.
    Switches between SetupScreen, LoginScreen, and MainWindow by destroying
    the current frame and replacing it.
    """

    def __init__(self) -> None:
        self._vault = VaultManager()

        self._root = tk.Tk()
        self._root.title("Password Vault")
        self._root.configure(bg="#1a1a2e")
        self._root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self._root.minsize(APP_MIN_WIDTH, APP_MIN_HEIGHT)
        self._root.resizable(True, True)

        # Center window on screen
        self._root.update_idletasks()
        x = (self._root.winfo_screenwidth() - APP_WIDTH) // 2
        y = (self._root.winfo_screenheight() - APP_HEIGHT) // 2
        self._root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}+{x}+{y}")

        # Set window icon if possible
        try:
            self._root.iconbitmap(default="")
        except Exception:
            pass

        self._current_frame: tk.Widget | None = None
        self._show_initial_screen()

    # ------------------------------------------------------------------
    # Screen switching
    # ------------------------------------------------------------------

    def _clear_frame(self) -> None:
        if self._current_frame is not None:
            self._current_frame.destroy()
            self._current_frame = None

    def _show_initial_screen(self) -> None:
        """Show setup or login depending on whether a vault exists."""
        if self._vault.is_new_vault:
            self._show_setup()
        else:
            self._show_login()

    def _show_setup(self) -> None:
        self._clear_frame()
        frame = SetupScreen(self._root, on_vault_created=self._on_vault_created)
        frame.pack(fill="both", expand=True)
        self._current_frame = frame
        self._root.title("Password Vault — Setup")

    def _show_login(self) -> None:
        self._clear_frame()
        frame = LoginScreen(self._root, on_unlock=self._on_unlock_attempted)
        frame.pack(fill="both", expand=True)
        self._current_frame = frame
        self._root.title("Password Vault — Unlock")

    def _show_main(self) -> None:
        self._clear_frame()
        frame = MainWindow(
            self._root,
            vault=self._vault,
            on_lock=self._on_vault_locked,
        )
        frame.pack(fill="both", expand=True)
        self._current_frame = frame
        self._root.title("Password Vault")

    # ------------------------------------------------------------------
    # Callbacks from screens
    # ------------------------------------------------------------------

    def _on_vault_created(self, master_password: str) -> None:
        """
        Called by SetupScreen after the user clicks 'Create Vault'.

        Creates the vault and transitions to the main window.
        The master password is not stored beyond this call.
        """
        try:
            self._vault.create_vault(master_password)
        except OSError:
            messagebox.showerror(
                "File Error",
                "Could not write vault file. Check that you have write permissions "
                "in the application directory.",
                parent=self._root,
            )
            return
        except Exception:
            logger.exception("Unexpected error creating vault.")
            messagebox.showerror(
                "Error",
                "An unexpected error occurred while creating the vault.",
                parent=self._root,
            )
            return
        finally:
            # Zero the local reference immediately
            master_password = ""

        self._show_main()

    def _on_unlock_attempted(self, master_password: str) -> None:
        """
        Called by LoginScreen after the user enters their password.

        Attempts vault decryption.  On failure, shows a generic error.
        The master password is not stored beyond this call.
        """
        try:
            self._vault.unlock(master_password)
        except FileNotFoundError:
            messagebox.showerror(
                "Vault Not Found",
                "No vault file was found. The application will restart setup.",
                parent=self._root,
            )
            self._show_setup()
            return
        except ValueError:
            # Generic message — do NOT reveal cryptographic details
            if isinstance(self._current_frame, LoginScreen):
                self._current_frame.show_error("Incorrect master password.")
            return
        except Exception:
            logger.exception("Unexpected error unlocking vault.")
            if isinstance(self._current_frame, LoginScreen):
                self._current_frame.show_error("Unable to unlock vault. Please try again.")
            return
        finally:
            master_password = ""

        self._show_main()

    def _on_vault_locked(self) -> None:
        """Called by MainWindow when the user clicks Lock."""
        self._show_login()

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._root.mainloop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception("Fatal error in application.")
        sys.exit(1)


if __name__ == "__main__":
    main()
