# Password Manager

A local desktop password manager built with Python, Tkinter, and SQLite.
Made as a college project, later cleaned up into something closer to a
normal Python codebase (package layout, tests, no giant single file).

## Features

- Master password login, checked with a constant-time comparison
- Entries encrypted at rest with Fernet (AES-128-CBC + HMAC), keyed off
  your master password through PBKDF2 (100k iterations)
- Passwords are only decrypted one at a time when you actually open an
  entry - the list view never touches plaintext
- Login lockout with increasing wait time after repeated wrong attempts
- Clipboard auto-clears 20 seconds after you copy a password
- Auto-locks after 2 minutes idle
- Built-in password generator with a strength indicator

## Project layout

```
passkit/
├── config.py       # constants (iteration counts, timeouts, etc.)
├── crypto.py        # key derivation, encryption, password generation
├── database.py       # SQLite access, no crypto logic lives here
├── manager.py       # ties crypto + database together, session/lockout state
└── gui/
    ├── style.py      # colors, fonts, ttk theming
    ├── dialogs.py     # login/setup/add/edit/generator popups
    └── app.py        # main window
main.py               # entry point
tests/                # pytest unit tests for crypto and manager layers
```

## Running it

```bash
pip install -r requirements.txt
python main.py
```

First run asks you to set a master password. After that, it's the login
screen every time.

## Running the tests

```bash
pip install pytest
pytest
```

## Security notes / limitations

- This encrypts the password *values*, not the SQLite file itself -
  website names and usernames are stored as plaintext. Don't put your
  vault file somewhere untrusted.
- The login lockout is in-memory only, so it resets if the app restarts.
  It slows down someone poking at the GUI, it isn't a defense against
  someone with direct access to `passwords.db`.
- No password recovery. If you forget the master password, the data is
  gone - that's the point of not storing it in a reversible form.

## Ideas for later

- Encrypt the whole database file, not just the password column
- Export/import (encrypted) backups
- A "breached password" check against a local list
