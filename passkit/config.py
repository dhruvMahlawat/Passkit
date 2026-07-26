# All the constants live here so nothing is hardcoded three files deep.

import os

# Where the vault lives. Kept next to the app by default, override with an
# env var if you want to point at a different location (e.g. for tests).
DB_PATH = os.environ.get("VAULT_DB_PATH", "passwords.db")

# PBKDF2 settings. 100k iterations is OWASP's old minimum for SHA-256 based
# PBKDF2 - fine for a local tool, would bump this on anything internet facing.
PBKDF2_ITERATIONS = 100_000
SALT_SIZE = 16  # bytes

MIN_MASTER_PASSWORD_LENGTH = 8

# Lock the app out after too many wrong master password attempts, doubling
# the wait each time. Resets if the process restarts - it's a deterrent for
# someone poking at the GUI, not a substitute for full-disk encryption.
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_BASE_SECONDS = 5

# Clipboard is wiped this many seconds after a "Copy" action, but only if
# the clipboard still holds the password we put there (so we don't nuke
# something else the user copied in the meantime).
CLIPBOARD_CLEAR_SECONDS = 20

# Password generator defaults
DEFAULT_PASSWORD_LENGTH = 16
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64
