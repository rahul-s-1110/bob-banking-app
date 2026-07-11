"""
tests.py — Unit and integration tests for the banking application.

Run with:
    cd BACKEND
    python -m pytest tests.py -v
  or
    python -m unittest tests -v
"""
import os
import sys
import tempfile
import sqlite3
import unittest

# Make sure BACKEND imports resolve
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("SECRET_KEY", "test-secret-key")

from werkzeug.security import generate_password_hash, check_password_hash


# ---------------------------------------------------------------------------
# Helpers — build an isolated in-memory test app
# ---------------------------------------------------------------------------

def create_test_app(db_path: str):
    """Return a Flask test application that uses *db_path* as its database."""
    # Monkey-patch DATABASE before importing app so it uses our test DB
    import db as db_module
    db_module.DATABASE = db_path

    # Re-import app with patched db
    import importlib
    import app as app_module
    importlib.reload(app_module)

    test_app = app_module.app
    test_app.config["TESTING"] = True
    test_app.config["WTF_CSRF_ENABLED"] = False
    return test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def setup_test_db(db_path: str):
    """Create tables and seed one test user for tests."""
    import db as db_module
    db_module.DATABASE = db_path
    db_module.init_db()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    password_hash = generate_password_hash("testpass")
    cursor = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        ("testuser", password_hash),
    )
    user_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO accounts (user_id, balance) VALUES (?, ?)",
        (user_id, 500.00),
    )
    conn.commit()
    conn.close()
    return user_id


# ---------------------------------------------------------------------------
# Unit tests — password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing(unittest.TestCase):
    def test_correct_password_matches(self):
        hashed = generate_password_hash("mypassword")
        self.assertTrue(check_password_hash(hashed, "mypassword"))

    def test_wrong_password_does_not_match(self):
        hashed = generate_password_hash("mypassword")
        self.assertFalse(check_password_hash(hashed, "wrongpassword"))


# ---------------------------------------------------------------------------
# Unit tests — accounts logic (using a real temp SQLite file)
# ---------------------------------------------------------------------------

class TestAccountsLogic(unittest.TestCase):

    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        self.db_file.close()
        self.user_id = setup_test_db(self.db_path)

        self.flask_app = create_test_app(self.db_path)
        # Push a request context so flask.flash() works inside unit tests
        self.ctx = self.flask_app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()
        os.unlink(self.db_path)

    def test_get_balance_returns_initial_balance(self):
        from accounts import get_balance
        balance = get_balance(self.user_id)
        self.assertAlmostEqual(balance, 500.00)

    def test_deposit_positive_amount(self):
        from accounts import apply_deposit, get_balance
        result = apply_deposit(self.user_id, "200")
        self.assertTrue(result)
        self.assertAlmostEqual(get_balance(self.user_id), 700.00)

    def test_deposit_zero_fails(self):
        from accounts import apply_deposit, get_balance
        result = apply_deposit(self.user_id, "0")
        self.assertFalse(result)
        self.assertAlmostEqual(get_balance(self.user_id), 500.00)

    def test_deposit_negative_fails(self):
        from accounts import apply_deposit, get_balance
        result = apply_deposit(self.user_id, "-50")
        self.assertFalse(result)
        self.assertAlmostEqual(get_balance(self.user_id), 500.00)

    def test_deposit_non_numeric_fails(self):
        from accounts import apply_deposit
        result = apply_deposit(self.user_id, "abc")
        self.assertFalse(result)

    def test_withdrawal_less_than_balance_succeeds(self):
        from accounts import apply_withdrawal, get_balance
        result = apply_withdrawal(self.user_id, "100")
        self.assertTrue(result)
        self.assertAlmostEqual(get_balance(self.user_id), 400.00)

    def test_withdrawal_exact_balance_succeeds(self):
        from accounts import apply_withdrawal, get_balance
        result = apply_withdrawal(self.user_id, "500")
        self.assertTrue(result)
        self.assertAlmostEqual(get_balance(self.user_id), 0.00)

    def test_withdrawal_exceeds_balance_fails(self):
        from accounts import apply_withdrawal, get_balance
        result = apply_withdrawal(self.user_id, "999")
        self.assertFalse(result)
        self.assertAlmostEqual(get_balance(self.user_id), 500.00)

    def test_withdrawal_zero_fails(self):
        from accounts import apply_withdrawal
        result = apply_withdrawal(self.user_id, "0")
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# Integration tests — full request / response cycle via test client
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):

    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        self.db_file.close()
        self.user_id = setup_test_db(self.db_path)

        self.flask_app = create_test_app(self.db_path)
        self.client = self.flask_app.test_client()

    def tearDown(self):
        os.unlink(self.db_path)

    # --- helpers ---

    def login(self, username="testuser", password="testpass"):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

    # --- auth ---

    def test_root_redirects_to_login(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_login_success_redirects_to_dashboard(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_login_wrong_password_rerenders_login(self):
        resp = self.login(password="wrongpassword")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Invalid username or password", resp.data)

    def test_dashboard_without_session_redirects_to_login(self):
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])

    def test_logout_clears_session_and_redirects(self):
        self.login()
        resp = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login", resp.headers["Location"])
        # After logout, dashboard should redirect to login
        resp2 = self.client.get("/dashboard")
        self.assertEqual(resp2.status_code, 302)

    # --- deposit flow ---

    def test_deposit_valid_amount(self):
        self.login()
        resp = self.client.post(
            "/deposit",
            data={"amount": "150"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"650", resp.data)  # new balance 500 + 150

    # --- withdrawal flow ---

    def test_withdrawal_insufficient_funds(self):
        self.login()
        resp = self.client.post(
            "/withdraw",
            data={"amount": "9999"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Insufficient funds", resp.data)

    def test_deposit_then_withdraw(self):
        self.login()
        self.client.post("/deposit", data={"amount": "200"}, follow_redirects=True)
        resp = self.client.post(
            "/withdraw",
            data={"amount": "300"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"400", resp.data)  # 500 + 200 - 300 = 400


if __name__ == "__main__":
    unittest.main(verbosity=2)
