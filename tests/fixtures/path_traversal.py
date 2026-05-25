"""File serving utility — CVE pattern: path traversal via user-controlled input."""
import os


UPLOAD_DIR = "/var/app/uploads"
REPORT_DIR = "/var/app/reports"


def read_user_file(filename: str) -> bytes:
    # Vulnerable: no sanitization — attacker can pass "../../etc/passwd"
    full_path = os.path.join(UPLOAD_DIR, filename)
    with open(full_path, "rb") as f:
        return f.read()


def serve_report(report_name: str) -> str:
    # Vulnerable: direct concatenation allows directory traversal
    path = REPORT_DIR + "/" + report_name
    with open(path) as f:
        return f.read()


def delete_temp_file(user_id: str, filename: str) -> bool:
    # Vulnerable: both segments are user-controlled
    target = f"/tmp/{user_id}/{filename}"
    if os.path.exists(target):
        os.remove(target)
        return True
    return False
