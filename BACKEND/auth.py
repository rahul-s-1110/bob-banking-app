"""
auth.py — Authentication helpers: login, logout, login_required decorator.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request, render_template
from werkzeug.security import check_password_hash
from db import get_db


def login_required(f):
    """Decorator that redirects unauthenticated users to /login."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def handle_login():
    """
    Process a POST /login request.
    Returns a Response object (redirect or re-rendered login template).
    """
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username:
        flash("Username is required.", "danger")
        return render_template("login.html")

    if not password:
        flash("Password is required.", "danger")
        return render_template("login.html")

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Invalid username or password.", "danger")
        return render_template("login.html")

    session.clear()
    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    return redirect(url_for("dashboard"))


def handle_logout():
    """Process a GET /logout request."""
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))
