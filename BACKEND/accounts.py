"""
accounts.py — Account balance queries, deposit and withdrawal logic.
"""
from datetime import datetime, timezone
from flask import flash
from db import get_db


def get_balance(user_id: int) -> float:
    """Return the current balance for the given user, or 0.0 if not found."""
    db = get_db()
    row = db.execute(
        "SELECT balance FROM accounts WHERE user_id = ?", (user_id,)
    ).fetchone()
    return float(row["balance"]) if row else 0.0


def apply_deposit(user_id: int, amount_str: str) -> bool:
    """
    Validate and apply a deposit.
    Returns True on success, False on validation failure (flash messages set).
    """
    if not amount_str or not amount_str.strip():
        flash("Amount is required.", "danger")
        return False

    try:
        amount = float(amount_str)
    except ValueError:
        flash("Please enter a valid amount.", "danger")
        return False

    if amount <= 0:
        flash("Deposit amount must be greater than zero.", "danger")
        return False

    db = get_db()
    try:
        account = db.execute(
            "SELECT account_id FROM accounts WHERE user_id = ?", (user_id,)
        ).fetchone()
        if account is None:
            flash("Account not found.", "danger")
            return False

        db.execute(
            "UPDATE accounts SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id),
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO transactions (account_id, type, amount, timestamp) "
            "VALUES (?, 'deposit', ?, ?)",
            (account["account_id"], amount, now),
        )
        db.commit()
        flash(f"Successfully deposited ${amount:,.2f}.", "success")
        return True
    except Exception:
        db.rollback()
        flash("An error occurred while processing your deposit.", "danger")
        return False


def apply_withdrawal(user_id: int, amount_str: str) -> bool:
    """
    Validate and apply a withdrawal.
    Returns True on success, False on validation failure (flash messages set).
    """
    if not amount_str or not amount_str.strip():
        flash("Amount is required.", "danger")
        return False

    try:
        amount = float(amount_str)
    except ValueError:
        flash("Please enter a valid amount.", "danger")
        return False

    if amount <= 0:
        flash("Withdrawal amount must be greater than zero.", "danger")
        return False

    db = get_db()
    try:
        account = db.execute(
            "SELECT account_id, balance FROM accounts WHERE user_id = ?", (user_id,)
        ).fetchone()
        if account is None:
            flash("Account not found.", "danger")
            return False

        current_balance = float(account["balance"])
        if amount > current_balance:
            flash("Insufficient funds.", "danger")
            return False

        db.execute(
            "UPDATE accounts SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id),
        )
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "INSERT INTO transactions (account_id, type, amount, timestamp) "
            "VALUES (?, 'withdrawal', ?, ?)",
            (account["account_id"], amount, now),
        )
        db.commit()
        flash(f"Successfully withdrew ${amount:,.2f}.", "success")
        return True
    except Exception:
        db.rollback()
        flash("An error occurred while processing your withdrawal.", "danger")
        return False
