from passkit import crypto


def test_encrypt_decrypt_roundtrip():
    key = crypto.derive_encryption_key("correct-horse", crypto.new_salt())
    vault = crypto.Vault(key)

    token = vault.encrypt("hunter2")
    assert token != "hunter2"
    assert vault.decrypt(token) == "hunter2"


def test_wrong_key_fails_to_decrypt():
    salt = crypto.new_salt()
    vault_a = crypto.Vault(crypto.derive_encryption_key("password-a", salt))
    vault_b = crypto.Vault(crypto.derive_encryption_key("password-b", salt))

    token = vault_a.encrypt("secret")
    try:
        vault_b.decrypt(token)
        assert False, "expected decryption to fail with the wrong key"
    except ValueError:
        pass


def test_master_password_verification():
    salt = crypto.new_salt()
    stored_hash = crypto.hash_master_password("my-master-pw", salt)

    assert crypto.verify_master_password("my-master-pw", salt, stored_hash)
    assert not crypto.verify_master_password("wrong-pw", salt, stored_hash)


def test_generated_password_respects_length():
    pw = crypto.generate_password(length=20, use_symbols=False)
    assert len(pw) == 20
    assert all(c.isalnum() for c in pw)


def test_password_strength_labels():
    assert crypto.password_strength("abc") == "weak"
    assert crypto.password_strength("abcdefgh1") == "medium"
    assert crypto.password_strength("Tr0ub4dor&Zebra!") == "strong"
