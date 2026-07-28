# Passkit

A local desktop password manager built with Python, Flet and SQLite.


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
- Change master password from inside the app - re-encrypts every saved
  entry under the new password

## No "forgot password"

This is intentional, not an oversight. The master password isn't stored
anywhere - it's the input to the key derivation function that produces
your encryption key. There's nothing to "reset" it to, because nobody,
including this app, ever has a copy of it to check against besides a
one-way hash. If you lose it, the vault contents are unrecoverable.

If you want to change it while you still remember it, use the
"Change master password" button in the app - that's the supported path.

## Project layout

```
passkit/
├── config.py       # constants (iteration counts, timeouts, etc.)
├── crypto.py        # key derivation, encryption, password generation
├── database.py       # SQLite access, no crypto logic lives here
├── manager.py       # ties crypto + database together, session/lockout state
└── gui/
    ├── style.py      # colors, cards, reusable Flet style helpers
    ├── screens.py     # full-screen setup and login views
    ├── dialogs.py     # add/edit/generate/view/change-password modals
    └── app.py        # main vault view, wiring everything together
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
