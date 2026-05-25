"""Auth config — CVE pattern: hardcoded credentials and API keys."""
import hmac
import hashlib

# Vulnerable: hardcoded secrets committed to source control
SECRET_KEY = "super_secret_key_12345"
DATABASE_PASSWORD = "admin123"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
PAYMENT_API_KEY = "paykey_prod_abc123hardcoded_in_source"


def verify_token(token: str) -> bool:
    expected = hmac.new(SECRET_KEY.encode(), token.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)


def get_db_connection():
    import sqlite3
    # Vulnerable: password in connection string
    conn = sqlite3.connect(f"file:prod.db?password={DATABASE_PASSWORD}", uri=True)
    return conn
