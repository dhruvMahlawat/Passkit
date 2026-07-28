"""The layer the GUI actually talks to. Handles login/lockout state and
makes sure decryption only ever happens for one entry at a time, on demand.
"""

import time
from dataclasses import dataclass

from . import config, crypto
from .database import Database, EntryMeta


class LockedOutError(Exception):
    """Raised when someone has failed the master password too many times."""
    def __init__(self, seconds_remaining: float):
        self.seconds_remaining = seconds_remaining
        super().__init__(f"locked out for {seconds_remaining:.0f}s")


@dataclass
class Entry:
    id: int
    website: str
    username: str
    password: str
    created_at: str
    modified_at: str


class PasswordManager:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db = Database(db_path)
        self._vault: crypto.Vault | None = None
        self._failed_attempts = 0
        self._locked_until = 0.0

    # --- session state -------------------------------------------------

    @property
    def is_unlocked(self) -> bool:
        return self._vault is not None

    def has_master_password(self) -> bool:
        return self.db.has_master_record()

    def lock(self):
        """Drop the derived key from memory. Call this on logout/idle timeout."""
        self._vault = None

    # --- authentication --------------------------------------------------

    def set_master_password(self, password: str):
        if len(password) < config.MIN_MASTER_PASSWORD_LENGTH:
            raise ValueError(f"master password needs at least {config.MIN_MASTER_PASSWORD_LENGTH} characters")

        salt = crypto.new_salt()
        password_hash = crypto.hash_master_password(password, salt)
        self.db.save_master_record(salt, password_hash)
        self._vault = crypto.Vault(crypto.derive_encryption_key(password, salt))

    def login(self, password: str) -> bool:
        remaining = self._lockout_remaining()
        if remaining > 0:
            raise LockedOutError(remaining)

        record = self.db.load_master_record()
        if record is None:
            return False

        if crypto.verify_master_password(password, record.salt, record.password_hash):
            self._failed_attempts = 0
            self._vault = crypto.Vault(crypto.derive_encryption_key(password, record.salt))
            return True

        self._failed_attempts += 1
        if self._failed_attempts >= config.MAX_LOGIN_ATTEMPTS:
            backoff = config.LOCKOUT_BASE_SECONDS * (2 ** (self._failed_attempts - config.MAX_LOGIN_ATTEMPTS))
            self._locked_until = time.monotonic() + backoff
        return False

    def _lockout_remaining(self) -> float:
        remaining = self._locked_until - time.monotonic()
        return max(0.0, remaining)

    def change_master_password(self, current_password: str, new_password: str):
        """Re-encrypts every saved entry under a new master password.

        There's no "forgot password" recovery in this app on purpose - the
        master password IS the encryption key, there's nothing to reset it
        to. This is the supported way to change it instead.
        """
        record = self.db.load_master_record()
        if record is None or not crypto.verify_master_password(current_password, record.salt, record.password_hash):
            raise ValueError("current master password is incorrect")

        if len(new_password) < config.MIN_MASTER_PASSWORD_LENGTH:
            raise ValueError(f"master password needs at least {config.MIN_MASTER_PASSWORD_LENGTH} characters")

        old_vault = crypto.Vault(crypto.derive_encryption_key(current_password, record.salt))

        new_salt = crypto.new_salt()
        new_vault = crypto.Vault(crypto.derive_encryption_key(new_password, new_salt))

        # Re-encrypt everything before committing the new master record, so
        # a crash partway through doesn't leave the vault in a state where
        # the master password no longer matches the data.
        for meta in self.db.list_entries():
            encrypted = self.db.get_encrypted_password(meta.id)
            plaintext = old_vault.decrypt(encrypted)
            self.db.replace_encrypted_password(meta.id, new_vault.encrypt(plaintext))

        new_hash = crypto.hash_master_password(new_password, new_salt)
        self.db.save_master_record(new_salt, new_hash)
        self._vault = new_vault

    # --- entries -----------------------------------------------------------

    def _require_unlocked(self):
        if self._vault is None:
            raise RuntimeError("vault is locked - log in first")

    def list_entries(self, search: str = "") -> list[EntryMeta]:
        """Metadata only. Nothing here is decrypted."""
        return self.db.list_entries(search)

    def get_entry(self, entry_id: int, meta: EntryMeta) -> Entry:
        """Decrypt exactly one entry - called only when the user opens it."""
        self._require_unlocked()
        encrypted = self.db.get_encrypted_password(entry_id)
        if encrypted is None:
            raise ValueError("entry not found")
        password = self._vault.decrypt(encrypted)
        return Entry(
            id=meta.id,
            website=meta.website,
            username=meta.username,
            password=password,
            created_at=meta.created_at,
            modified_at=meta.modified_at,
        )

    def add_entry(self, website: str, username: str, password: str) -> int:
        self._require_unlocked()
        encrypted = self._vault.encrypt(password)
        return self.db.insert_entry(website, username, encrypted)

    def update_entry(self, entry_id: int, website: str, username: str, password: str):
        self._require_unlocked()
        encrypted = self._vault.encrypt(password)
        self.db.update_entry(entry_id, website, username, encrypted)

    def delete_entry(self, entry_id: int):
        self.db.delete_entry(entry_id)

    @staticmethod
    def generate_password(length: int = config.DEFAULT_PASSWORD_LENGTH, use_symbols: bool = True) -> str:
        return crypto.generate_password(length, use_symbols)

    @staticmethod
    def password_strength(password: str) -> str:
        return crypto.password_strength(password)
