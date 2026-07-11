"""
db.py — SQLite connection management and schema initialisation.
"""
import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), "banking.db")


def get_db():
    """Open (or reuse) the database connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row  # access columns by name
    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the tables if they do not yet exist."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS accounts (
            account_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL UNIQUE REFERENCES users(user_id),
            balance    REAL    NOT NULL DEFAULT 0.00
        );

        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER  PRIMARY KEY AUTOINCREMENT,
            account_id     INTEGER  NOT NULL REFERENCES accounts(account_id),
            type           TEXT     NOT NULL CHECK(type IN ('deposit','withdrawal')),
            amount         REAL     NOT NULL,
            timestamp      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()
    db.close()


def register_teardown(app):
    """Register the close_db teardown with a Flask app instance."""
    app.teardown_appcontext(close_db)
