# Encrypted Password Vault

A local, offline password manager built in Python. All credentials are encrypted with **AES-256-GCM** and the encryption key is derived from a master password using **scrypt**. The vault file (`vault.enc`) contains only encrypted ciphertext — no plaintext credentials are ever written to disk.

---

## Features

- 🔐 **AES-256-GCM** authenticated encryption (confidentiality + integrity)
- 🧂 **scrypt** key derivation (memory-hard, GPU-resistant)
- 🔑 Master password **never stored** — only used to derive the encryption key
- 📋 **Auto-clearing clipboard** — password is wiped after 30 seconds (only if unchanged)
- 🔎 **Live search** across websites and usernames (in-RAM, no disk writes)
- 🎲 **Secure password generator** (uses `secrets` module, not `random`)
- 🔒 **Auto-lock** after 5 minutes of inactivity
- ✏️ Add, edit, delete password entries
- 🗒️ Optional notes per entry
- 🌐 **100% offline** — no network, no cloud, no database server

---

## Technologies Used

| Component | Library / Module |
|-----------|-----------------|
| GUI | `tkinter` (Python stdlib) |
| Encryption | `cryptography` (PyPI) |
| KDF | `cryptography.hazmat.primitives.kdf.scrypt` |
| Cipher | `cryptography.hazmat.primitives.ciphers.aead.AESGCM` |
| Secure random | `secrets` (Python stdlib) |
| Clipboard | `pyperclip` (PyPI) |
| Vault format | `json` + `base64` (Python stdlib) |
| Testing | `pytest` (PyPI) |

---

## How Encryption Works

### Security Architecture

```
Master Password
      │
      ▼
 Random Salt (32 bytes, stored in vault.enc)
      │
      ▼
  scrypt (N=2¹⁷, r=8, p=1)
      │
      ▼
 32-byte AES-256 Key  ◄── NEVER stored
      │
      ▼
 AES-256-GCM
      │           ┌─ unique nonce (12 bytes, stored in vault.enc)
      ▼           │
 Encrypted Vault  ◄── only this is on disk
```

### Why scrypt?

scrypt is a **memory-hard** key derivation function. Unlike PBKDF2, it requires large amounts of RAM to compute, making brute-force attacks on the master password:

- **Expensive on CPUs** (slow sequential computation)
- **Very expensive on GPUs** (large memory requirement defeats parallelism)
- **Nearly impossible on ASICs** (memory bandwidth is the bottleneck)

Parameters used: `N=131072 (2¹⁷), r=8, p=1` — the OWASP-recommended baseline.

### Why AES-256-GCM?

AES-256-GCM provides **authenticated encryption**:

- **AES-256** — 256-bit key, industry standard symmetric cipher
- **GCM mode** — provides both encryption *and* an authentication tag
- Any tampering with the ciphertext causes decryption to fail with an authentication error
- The application cannot distinguish "wrong password" from "tampered vault" — both show the same error message (by design, to avoid information leakage)

### How the Master Password Works

1. On first launch: user chooses a master password → random salt generated → scrypt derives key → empty vault encrypted → salt + nonce + ciphertext saved to `vault.enc`.
2. On unlock: user enters master password → same scrypt computation with stored salt → attempt AES-GCM decryption → success means correct password.
3. The master password is **never written anywhere**. It lives only in RAM for the duration of the unlock call.

---

## Vault File Format

`vault.enc` contains:

```json
{
  "version": 1,
  "kdf": "scrypt",
  "salt": "<base64-encoded 32-byte random salt>",
  "nonce": "<base64-encoded 12-byte AES-GCM nonce>",
  "ciphertext": "<base64-encoded encrypted+authenticated credentials blob>"
}
```

- **salt** — public, needed to re-derive the key on next unlock
- **nonce** — public, must be unique per encryption (a fresh nonce is generated on every save)
- **ciphertext** — the encrypted JSON list of all credentials, plus the 16-byte GCM authentication tag

Opening `vault.enc` in a text editor reveals only Base64 blobs — no usernames or passwords.

---

## How Clipboard Auto-Clearing Works

1. User clicks **Copy** on an entry.
2. The password is placed in the system clipboard via `pyperclip`.
3. The copied string is saved in memory.
4. A background timer thread starts (30 seconds).
5. When the timer fires:
   - Read current clipboard content.
   - **Only clear if the clipboard still contains our password string.**
   - If the user has copied something else, we do **not** overwrite it.
6. A status label counts down in the UI.

---

## Installation

### Prerequisites

- Python 3.11 or newer
- pip

### Steps

```bash
# Clone the repository
git clone https://github.com/AtharvaThakre/Encrypted-Password-Vault.git
cd Encrypted-Password-Vault

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Run Tests

```bash
pytest tests/ -v
```

> **Note:** Tests for crypto operations (scrypt) may take a few seconds due to the intentionally expensive key derivation.

---

## Project Structure

```
encrypted-password-vault/
│
├── main.py                    # Entry point, screen routing, Tk root
├── requirements.txt           # Third-party dependencies
├── README.md                  # This file
├── .gitignore
│
├── vault/
│   ├── __init__.py
│   ├── crypto.py              # scrypt KDF, AES-256-GCM encrypt/decrypt
│   ├── storage.py             # vault.enc read/write, JSON/Base64 serialisation
│   ├── models.py              # VaultEntry dataclass
│   └── manager.py             # High-level vault CRUD, lock/unlock lifecycle
│
├── gui/
│   ├── __init__.py
│   ├── setup.py               # First-run setup screen
│   ├── login.py               # Unlock screen
│   ├── main_window.py         # Main vault UI (list, search, copy, lock)
│   ├── entry_dialog.py        # Add / Edit entry dialog
│   └── password_generator.py  # Secure password generator dialog
│
├── utils/
│   ├── __init__.py
│   └── clipboard.py           # Clipboard copy + auto-clear logic
│
└── tests/
    ├── __init__.py
    ├── test_crypto.py          # KDF, encrypt/decrypt, tamper detection
    ├── test_storage.py         # File I/O, serialisation, error cases
    └── test_password_generator.py  # Generator length, charset, uniqueness
```

---

## Security Limitations

This is an academic/project application. Be aware of the following limitations:

1. **Python memory management** — Python does not guarantee immediate memory zeroing. Sensitive data (key, decrypted entries) is dereferenced on lock but may linger in memory until garbage-collected.

2. **Clipboard** — The clipboard is a shared OS resource. Other applications running on the same machine can read it during the 30-second window before auto-clear.

3. **Screen capture** — Passwords shown in the UI (via show/hide toggle) can be captured by screen-recording software.

4. **Single-user, single-device** — The vault is a local file. No sync, no backup. If `vault.enc` is deleted and no backup exists, credentials are permanently lost.

5. **Master password strength** — The application enforces minimum requirements, but the security of the entire vault depends on the entropy of the master password.

6. **No protection against keyloggers** — A keylogger on the host machine can capture the master password as it is typed.

7. **File permissions** — `vault.enc` is created with default OS file permissions. On multi-user systems, ensure appropriate access controls.

---

## License

MIT License. See `LICENSE` for details.
..