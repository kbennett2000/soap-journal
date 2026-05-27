from soap_journal.core.passwords import hash_password, verify_password


def test_hash_then_verify_returns_true() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_fails_for_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("wrong password", hashed) is False


def test_hash_is_not_plaintext() -> None:
    plain = "password123"
    hashed = hash_password(plain)
    assert plain not in hashed
    assert hashed.startswith("$argon2")


def test_hashes_are_salted_and_distinct() -> None:
    a = hash_password("same-password")
    b = hash_password("same-password")
    assert a != b
    assert verify_password("same-password", a)
    assert verify_password("same-password", b)
