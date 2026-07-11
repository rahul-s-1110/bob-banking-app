"""
app.py — Flask application entry point.
Registers all routes and wires together auth, accounts, and database layers.
"""
import os
import sys

# Ensure imports resolve from the BACKEND folder when running via `flask run`
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, redirect, url_for, render_template, request, session, flash

from db import get_db, init_db, register_teardown
from auth import handle_login, handle_logout, login_required
from accounts import get_balance, apply_deposit, apply_withdrawal

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

TEMPLATE_FOLDER = os.path.join(
    os.path.dirname(__file__), "..", "FRONTEND", "templates"
)

app = Flask(__name__, template_folder=TEMPLATE_FOLDER)

# Secret key — read from environment; fall back to a dev-only default.
# NEVER use the dev default in production.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Session cookie hardening (effective when served over HTTPS in production)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

register_teardown(app)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Redirect root to login."""
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return handle_login()
    return render_template("login.html")


@app.route("/logout")
def logout():
    return handle_logout()


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session["user_id"]
    username = session["username"]
    balance = get_balance(user_id)
    return render_template(
        "dashboard.html",
        username=username,
        balance=f"{balance:,.2f}",
    )


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":
        apply_deposit(session["user_id"], request.form.get("amount", ""))
        return redirect(url_for("dashboard"))
    return render_template("deposit.html")


@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    user_id = session["user_id"]
    if request.method == "POST":
        amount = request.form.get("amount", "")

        if not amount or not amount.strip():
            flash("Amount is required", "danger")
            balance = get_balance(user_id)
            return render_template("withdraw.html", balance=f"{balance:,.2f}")

        try:
            amount_value = float(amount)
        except ValueError:
            amount_value = None

        if amount_value is None or amount_value <= 0:
            flash("Amount must be greater than zero", "danger")
            balance = get_balance(user_id)
            return render_template("withdraw.html", balance=f"{balance:,.2f}")

        if amount_value > get_balance(user_id):
            flash("Insufficient funds", "danger")
            balance = get_balance(user_id)
            return render_template("withdraw.html", balance=f"{balance:,.2f}")

        apply_withdrawal(user_id, amount)
        return redirect(url_for("dashboard"))
    balance = get_balance(user_id)
    return render_template("withdraw.html", balance=f"{balance:,.2f}")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(500)
def internal_error(e):
    return render_template("500.html"), 500


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Startup — initialise DB tables if they do not exist
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
