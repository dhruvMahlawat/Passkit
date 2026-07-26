import tempfile
import os

import pytest

from passkit.manager import LockedOutError, PasswordManager


@pytest.fixture
def manager():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # let PasswordManager create it fresh
    pm = PasswordManager(db_path=path)
    yield pm
    os.remove(path)


def test_setup_and_login(manager):
    manager.set_master_password("correct-horse-battery")
    manager.lock()

    assert manager.login("wrong-password") is False
    assert manager.login("correct-horse-battery") is True
    assert manager.is_unlocked


def test_add_and_read_back_entry(manager):
    manager.set_master_password("correct-horse-battery")
    entry_id = manager.add_entry("github.com", "dhruv", "s3cret!")

    entries = manager.list_entries()
    assert len(entries) == 1
    # metadata listing never carries the plaintext password
    assert not hasattr(entries[0], "password")

    full_entry = manager.get_entry(entry_id, entries[0])
    assert full_entry.password == "s3cret!"


def test_lockout_after_repeated_failures(manager):
    manager.set_master_password("correct-horse-battery")
    manager.lock()

    for _ in range(5):
        manager.login("wrong")

    with pytest.raises(LockedOutError):
        manager.login("wrong-again")
