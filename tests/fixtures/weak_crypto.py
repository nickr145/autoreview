"""Password and token utilities — CVE pattern: weak cryptographic primitives."""
import hashlib
import random
import os


def hash_password(password: str) -> str:
    # Vulnerable: MD5 is cryptographically broken for password hashing
    return hashlib.md5(password.encode()).hexdigest()


def hash_file(filepath: str) -> str:
    # Vulnerable: SHA1 is deprecated for integrity checks
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def generate_token(length: int = 32) -> str:
    # Vulnerable: random is not cryptographically secure
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choice(chars) for _ in range(length))


def generate_reset_code() -> int:
    # Vulnerable: random.randint is predictable
    return random.randint(100000, 999999)
