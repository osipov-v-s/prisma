"""Password hashing based on the standard-library scrypt implementation."""

import hashlib
import hmac
import os


ALGORITHM = "scrypt"
N = 2**14
R = 8
P = 1
KEY_LENGTH = 64


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Пароль должен содержать не менее 8 символов.")
    salt = os.urandom(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=N, r=R, p=P, dklen=KEY_LENGTH
    )
    return f"{ALGORITHM}${N}${R}${P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = bytes.fromhex(expected_hex)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False
