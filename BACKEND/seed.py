"""
seed.py — Seed the database with one demo customer account.
Run once:  python seed.py

Re-running will skip the insert if the user already exists.
"""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
from db import init_db, DATABASE

# ---------------------------------------------------------------------------
# Demo credentials — change as desired
# ---------------------------------------------------------------------------
DEMO_USERNAME = "customer"
DEMO_PASSWORD = "password123"
INITIAL_BALANCE = 1000.00


def seed():
    init_db()
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    try:
        existing = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", (DEMO_USERNAME,)
        ).fetchone()

        if existing:
            print(f"[seed] User '{DEMO_USERNAME}' already exists — skipping.")
            return

        password_hash = generate_password_hash(DEMO_PASSWORD)

        cursor = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (DEMO_USERNAME, password_hash),
        )
        user_id = cursor.lastrowid

        conn.execute(
            "INSERT INTO accounts (user_id, balance) VALUES (?, ?)",
            (user_id, INITIAL_BALANCE),
        )
        conn.commit()

        print(f"[seed] Created user '{DEMO_USERNAME}' (id={user_id}) "
              f"with balance ${INITIAL_BALANCE:,.2f}.")
        print(f"[seed] Login credentials:  username='{DEMO_USERNAME}'  "
              f"password='{DEMO_PASSWORD}'")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
