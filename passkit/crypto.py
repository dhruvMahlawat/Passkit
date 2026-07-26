"""Everything cryptography-related: deriving keys, encrypting entries,
generating passwords, and checking how strong a password is.

Nothing here touches the database or the GUI - keeping it isolated makes it
easy to unit test and easy to reason about (it's the part that actually
matters for security).
"""

import base64
import hashlib
import secrets
import string

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from . import config


def new_salt() -> bytes:
    return secrets.token_bytes(config.SALT_SIZE)


def derive_encryption_key(master_password: str, salt: bytes) -> bytes:
    """Turn the master password + salt into a Fernet-compatible key.

    This key is only ever kept in memory for the current session, never
    written to disk.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=config.PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def hash_master_password(master_password: str, salt: bytes) -> bytes:
    """Separate hash used only to *verify* the master password on login.

    Deliberately different from derive_encryption_key - if this hash ever
    leaked it shouldn't hand anyone the encryption key too.
    """
    return hashlib.pbkdf2_hmac(
        "sha256", master_password.encode(), salt, config.PBKDF2_ITERATIONS
    )


def verify_master_password(master_password: str, salt: bytes, stored_hash: bytes) -> bool:
    """Constant-time check so login doesn't leak timing information."""
    candidate = hash_master_password(master_password, salt)
    return secrets.compare_digest(candidate, stored_hash)


class Vault:
    """Thin wrapper around Fernet for a single unlocked session."""

    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        token = self._fernet.encrypt(plaintext.encode())
        return base64.b64encode(token).decode()

    def decrypt(self, ciphertext: str) -> str:
        token = base64.b64decode(ciphertext.encode())
        try:
            return self._fernet.decrypt(token).decode()
        except InvalidToken as exc:
            # Wrong key or corrupted row - surface it as something callers
            # can catch without leaking cryptography internals up the stack.
            raise ValueError("could not decrypt entry, vault key mismatch") from exc


def generate_password(length: int = config.DEFAULT_PASSWORD_LENGTH, use_symbols: bool = True) -> str:
    alphabet = string.ascii_letters + string.digits
    if use_symbols:
        alphabet += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # secrets.choice, not random.choice - random isn't a CSPRNG.
    return "".join(secrets.choice(alphabet) for _ in range(length))


def password_strength(password: str) -> str:
    """Rough strength label for the UI. Not a substitute for zxcvbn, just
    enough feedback to nudge people away from 'password1'.
    """
    if len(password) < 8:
        return "weak"

    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    variety = sum([has_lower, has_upper, has_digit, has_symbol])

    if len(password) >= 12 and variety >= 3:
        return "strong"
    if variety >= 2:
        return "medium"
    return "weak"
