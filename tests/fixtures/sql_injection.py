"""User lookup service — CVE pattern: SQL injection via string concatenation."""
import sqlite3


def get_user(db_path: str, user_id: str) -> dict | None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Vulnerable: user_id is concatenated directly into the query string
    query = "SELECT id, username, email FROM users WHERE id = " + user_id
    cursor.execute(query)
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "username": row[1], "email": row[2]}
    return None


def search_users(db_path: str, username: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Vulnerable: f-string interpolation into SQL
    cursor.execute(f"SELECT * FROM users WHERE username LIKE '%{username}%'")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "username": r[1]} for r in rows]
