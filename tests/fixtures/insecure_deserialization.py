"""Session cache — CVE pattern: insecure deserialization of untrusted data."""
import pickle
import base64
from typing import Any


def load_session(session_cookie: str) -> dict:
    # Vulnerable: pickle.loads on attacker-controlled cookie data
    raw = base64.b64decode(session_cookie)
    session = pickle.loads(raw)
    return session


def restore_job(job_payload: bytes) -> Any:
    # Vulnerable: arbitrary object reconstruction from queue payload
    return pickle.loads(job_payload)


def cache_get(key: str, store: dict) -> Any:
    if key in store:
        # Vulnerable: values were serialized with pickle and stored externally
        return pickle.loads(store[key])
    return None


def cache_set(key: str, value: Any, store: dict) -> None:
    store[key] = pickle.dumps(value)
