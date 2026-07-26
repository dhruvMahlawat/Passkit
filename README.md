# Passkit

A local password manager written in Python, using Tkinter for the UI and SQLite for storage. Started out as a college project, then I went back and cleaned it up into an actual package instead of one long script.

Everything runs on your machine. No server, no account, no syncing.

## What it does

- Master password login, checked with a constant-time comparison instead of a plain `==`
- Saved passwords are encrypted with Fernet (AES-128-CBC + HMAC). The key comes from your master password via PBKDF2-HMAC-SHA256, 100k iterations
- The entry list only shows website/username/last modified - passwords aren't decrypted until you actually open that one entry
- Get the master password wrong too many times and you get locked out for a bit, with the wait doubling each time
- Copying a password to clipboard clears it again after 20 seconds
- Vault locks itself after 2 minutes of no activity
- Password generator with adjustable length, symbols on/off, and a weak/medium/strong indicator
- Search box to filter entries as you type

## Layout

```
passkit/
├── config.py       # constants - iteration counts, timeouts, etc
├── crypto.py        # key derivation, encryption, password generation
├── database.py       # sqlite access, no crypto happens in here
├── manager.py       # glues crypto + database together, handles session/lockout
└── gui/
    ├── style.py      # colors, fonts, ttk theming
    ├── dialogs.py     # login/setup/add/edit/generator popups
    └── app.py        # main window
main.py               # entry point
tests/                # pytest tests for crypto.py and manager.py
```

Kept crypto and database separate on purpose - database.py never touches a decrypted password, it just moves encrypted blobs in and out of sqlite. Its `list_entries()` query doesn't even select the encrypted password column, so there's no accidental way to end up decrypting everything just to show the list. manager.py is the only thing that holds the actual session key, and it drops it as soon as you lock the vault.

The login check and the encryption key come from two separate hashes of your master password, so if the login hash ever leaked somehow it wouldn't also hand over the encryption key.

## Setup

Needs Python 3.10+ and Tkinter (usually bundled, but on some Linux distros you need `sudo apt install python3-tk` separately).

```bash
git clone https://github.com/dhruvMahlawat/Passkit.git
cd Passkit
pip install -r requirements.txt
python main.py
```

First launch asks you to set a master password (8 char minimum). After that it's just a login screen. There's no "forgot password" option - if you lose it, the vault is gone, that's kind of the point.

By default the db file is `passwords.db` next to the app. Set `VAULT_DB_PATH` if you want it somewhere else.

## Tests

```bash
pip install pytest
pytest
```

Covers the crypto round-trip stuff (encrypt/decrypt, wrong key failing correctly, password strength labeling) and the manager layer (login/lockout, adding an entry and reading it back).

## Known limitations

- Only the password values are encrypted, not the whole db file - website/username fields are plaintext in the sqlite file. Don't leave `passwords.db` somewhere someone else can grab it.
- The lockout counter is in memory only, so restarting the app resets it. It's just there to slow down someone messing with the GUI, not a real defense if someone has the db file directly.
- No cloud backup or export, so back up `passwords.db` yourself if you care about the data.

## Maybe later

- Encrypt the whole db, not just the password column
- Encrypted export/import for backups
- Check new passwords against a local breached-password list

## License

Nothing set yet, so normal copyright rules apply by default. Might add MIT later.