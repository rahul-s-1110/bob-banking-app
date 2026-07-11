# Banking Web Application — Step-by-Step Implementation Guide

> **Reference:** [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md)
> This guide translates the planning document into plain-English instructions for every implementation layer.
> It describes *what to do* and *why* — not line-by-line code.

---

## 1. Environment Setup

### 1.1 Prerequisites
Confirm that **Python 3.9 or later** is installed on your machine. You can verify this by checking the Python version in your terminal. If it is not installed, download it from python.org before continuing.

### 1.2 Create the Project Folder Structure
Create the top-level project directory, then create two sub-folders inside it: one named `FRONTEND` and one named `BACKEND`. Inside `FRONTEND`, create a `templates` sub-folder — Flask will look here for all HTML files. This mirrors the folder layout described in the implementation plan.

### 1.3 Set Up a Python Virtual Environment
Navigate into the `BACKEND` folder and create a virtual environment there. A virtual environment keeps the project's Python packages isolated from your system Python. Activate the environment before doing anything else; all subsequent `pip install` commands will install into this environment only.

- On macOS / Linux, activate with the `source` command pointing at `bin/activate`.
- On Windows, activate via `Scripts\activate`.

### 1.4 Install Dependencies
With the virtual environment active, install the following packages:

| Package | Purpose |
|---|---|
| `flask` | Web framework — routing, templates, session handling |
| `werkzeug` | Ships with Flask; provides password hashing utilities |
| `flask-session` *(optional)* | Server-side sessions if you want to avoid cookie-only sessions |

Once installed, create a `requirements.txt` file inside `BACKEND` by running `pip freeze > requirements.txt`. Anyone else setting up the project can reproduce your environment with `pip install -r requirements.txt`.

### 1.5 Verify Flask is Working
Create a minimal `app.py` in `BACKEND` that creates a Flask instance and defines a single `/` route returning the text "Hello, Bank". Run `flask run` from the `BACKEND` folder and confirm the browser shows the message. This smoke-test confirms the environment is correct before any real code is written.

---

## 2. Backend Implementation

### 2.1 Application Entry Point — `app.py`
`app.py` is the heart of the backend. Its responsibilities are:
- Create the Flask application instance.
- Set a **secret key** (a long random string) — this is required for session encryption. Never hardcode a production secret; read it from an environment variable.
- Register the template folder path, pointing Flask at `FRONTEND/templates/`.
- Import and register all routes (from `auth.py` and `accounts.py`).
- Call the database initialisation function on startup so that tables are created if they do not already exist.

### 2.2 Database Helper — `db.py`
This module manages everything related to the SQLite connection:
- Define a function `get_db()` that opens a connection to `banking.db` (stored in the `BACKEND` folder). Configure the connection to return rows as dictionary-like objects so columns can be accessed by name.
- Define an `init_db()` function that creates the three tables — `users`, `accounts`, and `transactions` — if they do not exist. Call this once when the application starts.
- Define a `close_db()` function and register it with Flask's teardown mechanism so the connection is always closed at the end of each request, preventing connection leaks.

### 2.3 Data Models — `models.py`
Define simple Python data structures (dataclasses or named tuples) that represent the three entities the application works with:
- **User** — holds `user_id`, `username`, and `password_hash`.
- **Account** — holds `account_id`, `user_id` (foreign key), and `balance`.
- **Transaction** — holds `transaction_id`, `account_id`, `type` (deposit or withdrawal), `amount`, and `timestamp`.

These models are not enforced by the database; they are used in Python code to pass data around in a structured way rather than using raw dictionaries everywhere.

### 2.4 Authentication Module — `auth.py`

#### Login Route (`POST /login`)
When the login form is submitted:
1. Read the `username` and `password` fields from the form data.
2. Query the `users` table for a row where the username matches.
3. If no user is found, flash an error message and re-render the login page.
4. If a user is found, use Werkzeug's `check_password_hash` to compare the submitted password against the stored hash. **Never compare passwords as plain text.**
5. If the hash check passes, store the `user_id` in Flask's `session` dictionary. This marks the user as logged in for subsequent requests.
6. Redirect the user to the `/dashboard` route.

#### Logout Route (`GET /logout`)
When the user clicks Logout:
1. Call `session.clear()` to remove all session data — this effectively logs the user out.
2. Redirect to the login page with an optional "You have been logged out" flash message.

#### `login_required` Decorator
Write a reusable decorator function that wraps any route handler. When a request arrives at a protected route, the decorator checks whether `user_id` is present in `session`. If it is not, the decorator immediately redirects to `/login`. If it is, the original route handler runs normally. Apply this decorator to every route except login itself.

### 2.5 Account & Transaction Logic — `accounts.py`

#### Get Balance
Write a `get_balance(user_id)` function that queries the `accounts` table for the row associated with the given `user_id` and returns the current balance. This is called by the dashboard route.

#### Deposit
Write an `apply_deposit(user_id, amount)` function that:
1. Validates the amount is a positive number greater than zero.
2. Opens a database transaction.
3. Increments the balance in the `accounts` row for the user.
4. Inserts a new row into `transactions` with type `"deposit"`, the amount, and the current timestamp.
5. Commits the transaction. If anything fails, roll back to leave the database unchanged.

#### Withdraw
Write an `apply_withdrawal(user_id, amount)` function that:
1. Validates the amount is a positive number greater than zero.
2. Fetches the current balance and confirms the amount does not exceed it.
3. Opens a database transaction.
4. Decrements the balance in the `accounts` row.
5. Inserts a new row into `transactions` with type `"withdrawal"`.
6. Commits the transaction. Roll back on any failure.

### 2.6 Route Handlers in `app.py`
Define the following routes, each calling the appropriate helper from `auth.py` or `accounts.py`:

| Method | Path | Handler logic |
|---|---|---|
| `GET` | `/` | Redirect to `/login` |
| `GET/POST` | `/login` | GET renders login form; POST calls auth login logic |
| `GET` | `/logout` | Calls logout logic, redirects to `/login` |
| `GET` | `/dashboard` | `login_required` — fetches balance, renders dashboard |
| `GET/POST` | `/deposit` | `login_required` — GET renders form; POST calls deposit logic |
| `GET/POST` | `/withdraw` | `login_required` — GET renders form; POST calls withdrawal logic |

### 2.7 Session Management
Flask sessions work by signing a cookie with the app's secret key. To use them:
- Store only the `user_id` in the session — nothing sensitive.
- Set `session.permanent = True` and configure `PERMANENT_SESSION_LIFETIME` if you want sessions to expire after a period of inactivity.
- Always call `session.clear()` on logout — do not just delete the `user_id` key.

### 2.8 Error Handling
- For unexpected server errors, register a Flask `@app.errorhandler(500)` that renders a simple "Something went wrong" page rather than exposing a stack trace.
- For unauthorised access to protected routes, the `login_required` decorator handles the redirect — no additional 401 handler is needed.
- For business-rule violations (negative amount, insufficient balance), use Flask's `flash()` function to pass an error message back to the template and re-render the form rather than raising an exception.

---

## 3. Frontend Implementation

All templates live in `FRONTEND/templates/`. Flask is configured to look there when `render_template()` is called.

### 3.1 Base Layout — `base.html`
Create a master template that all other pages extend. It should contain:
- The HTML `<head>` with a `<title>` block and the Bootstrap CSS CDN link.
- A navigation bar with the application name on the left and, when the user is logged in, a "Logout" link on the right.
- A content `{% block content %}` placeholder that child templates fill in.
- A section for displaying flash messages — iterate over `get_flashed_messages()` and show each one in a Bootstrap alert component (green for success, red for danger).

### 3.2 Login Page — `login.html`
Extends `base.html`. Contains:
- A centred Bootstrap card with the heading "Welcome to Bank".
- A form with `method="POST"` and `action="/login"`.
- Two input fields: `username` (text) and `password` (password type). Mark both as `required`.
- A "Login" submit button styled with Bootstrap's primary button class.
- No link to a registration page — account creation is handled by the seed script only.

### 3.3 Dashboard — `dashboard.html`
Extends `base.html`. Contains:
- A greeting showing the logged-in username (passed from the route as a template variable).
- A Bootstrap card prominently displaying the current balance (also passed as a template variable, formatted as currency).
- Two Bootstrap buttons or links: "Deposit Funds" pointing to `/deposit`, and "Withdraw Funds" pointing to `/withdraw`.
- The flash message area (inherited from `base.html`) will automatically show the result of the last deposit or withdrawal.

### 3.4 Deposit Form — `deposit.html`
Extends `base.html`. Contains:
- A Bootstrap card titled "Deposit Funds".
- A form with `method="POST"` and `action="/deposit"`.
- A single numeric input field for the deposit amount. Set `min="0.01"` and `step="0.01"` so the browser rejects zero and non-numeric values before the form even submits.
- A "Confirm Deposit" submit button.
- A "Back to Dashboard" link.

### 3.5 Withdrawal Form — `withdraw.html`
Extends `base.html`. Contains:
- A Bootstrap card titled "Withdraw Funds".
- Displays the current available balance so the customer knows the limit before submitting.
- A form with `method="POST"` and `action="/withdraw"`.
- A numeric input field for the withdrawal amount with the same `min` and `step` constraints as the deposit form.
- A "Confirm Withdrawal" submit button.
- A "Back to Dashboard" link.

### 3.6 Bootstrap Layout Principles
- Use Bootstrap's **grid system** (`container`, `row`, `col-*`) to centre forms on the page.
- Load Bootstrap **only from CDN** — no local files needed.
- Use Bootstrap **utility classes** (`mt-4`, `p-3`, `text-danger`) for spacing and colour rather than custom CSS.
- Keep all custom styling minimal; Bootstrap's defaults are sufficient for this application.

---

## 4. Integration Steps

### 4.1 Connect Flask to the Correct Template Folder
When creating the Flask app instance, pass the `template_folder` argument pointing at the absolute or relative path to `FRONTEND/templates/`. Flask's `render_template()` calls will resolve file names relative to this folder.

### 4.2 Connect Flask Routes to Templates
Each route handler should call `render_template('page.html', variable=value)` to pass data to the template. The template then reads the variable using Jinja2's `{{ variable }}` syntax. For example, the dashboard route passes `balance` and `username` to `dashboard.html`.

### 4.3 Connect Form Submissions to Route Logic
HTML forms use the `POST` method and point their `action` attribute at the corresponding Flask URL (e.g., `/deposit`). Flask reads submitted field values using `request.form['field_name']`. Always validate these values server-side — never trust client-side constraints alone.

### 4.4 Connect Flask to SQLite
The `get_db()` function in `db.py` opens a connection to `banking.db`. Every route that reads or writes data calls `get_db()` at the start and uses the connection for its queries. The connection is closed automatically at the end of the request by the teardown hook registered in `db.py`. The database file is created automatically by SQLite on the first connection if it does not exist.

### 4.5 Seed the Database
Write a small standalone Python script (e.g., `seed.py` in `BACKEND`) that:
1. Opens a connection to `banking.db`.
2. Calls `init_db()` to create the tables.
3. Inserts one user row with a username and a hashed password.
4. Inserts one account row for that user with a starting balance (e.g., 1000.00).
5. Closes the connection and prints a confirmation message.

Run this script once before the first application start. Do not run it again unless you want to reset the database, as it will create duplicate rows.

---

## 5. Validation Rules

### 5.1 Login Validation
| Check | Location | Action on failure |
|---|---|---|
| Username field is not blank | Server (Flask) | Flash "Username is required" and re-render login |
| Password field is not blank | Server (Flask) | Flash "Password is required" and re-render login |
| Username exists in `users` table | Server (Flask) | Flash "Invalid username or password" (do not reveal which is wrong) |
| Password hash matches stored hash | Server (Flask) | Flash "Invalid username or password" |

Always use a single generic error message for credential failures to prevent user enumeration attacks.

### 5.2 Balance Validation (on Dashboard)
- The balance is read directly from the database on every page load of the dashboard — never cache it in the session or a template variable between requests.
- Format the balance as a two-decimal-place currency value before passing it to the template.

### 5.3 Deposit Checks
| Check | Location | Action on failure |
|---|---|---|
| Amount field is not blank | Server | Flash error, re-render deposit form |
| Amount can be parsed as a decimal number | Server | Flash "Please enter a valid amount" |
| Amount is greater than zero | Server | Flash "Deposit amount must be greater than zero" |

There is no upper limit on deposits for this application.

### 5.4 Withdrawal Checks
| Check | Location | Action on failure |
|---|---|---|
| Amount field is not blank | Server | Flash error, re-render withdraw form |
| Amount can be parsed as a decimal number | Server | Flash "Please enter a valid amount" |
| Amount is greater than zero | Server | Flash "Withdrawal amount must be greater than zero" |
| Amount does not exceed current balance | Server | Flash "Insufficient funds" |

Re-render the withdrawal form with the current balance visible so the customer can correct their input.

---

## 6. Testing

### 6.1 Unit Tests
Write unit tests for the pure business-logic functions — these do not require a running Flask server or a real database:

- **`apply_deposit`** — test with a positive amount (expect balance to increase), with zero (expect error), and with a negative amount (expect error).
- **`apply_withdrawal`** — test with an amount less than balance (expect success), with an amount equal to balance (expect success — edge case), and with an amount greater than balance (expect "Insufficient funds" error).
- **Password hashing helper** — confirm that hashing a password and checking it with `check_password_hash` returns `True`, and that a wrong password returns `False`.

Use Python's built-in `unittest` module or `pytest`. Mock the database calls using a test database file in a temporary directory so tests do not touch `banking.db`.

### 6.2 Integration Tests
Use Flask's built-in test client (`app.test_client()`) to test the full request–response cycle:

- **Login flow** — POST valid credentials, expect a redirect to `/dashboard` and a session cookie containing `user_id`.
- **Login failure** — POST invalid credentials, expect re-render of the login page with an error flash message.
- **Protected route without session** — GET `/dashboard` without logging in, expect a redirect to `/login`.
- **Deposit flow** — log in, POST a valid deposit amount to `/deposit`, expect a redirect to `/dashboard` and an updated balance.
- **Withdrawal — insufficient funds** — POST an amount greater than balance, expect the withdraw page to re-render with "Insufficient funds".
- **Logout** — GET `/logout`, expect a redirect to `/login` and the session to be cleared.

Use a separate in-memory SQLite database for integration tests to keep them isolated from development data.

### 6.3 Manual Testing Checklist
Run through this checklist in the browser after every significant change:

- [ ] Visiting `/` redirects to `/login`.
- [ ] Login with wrong password shows an error and stays on login page.
- [ ] Login with correct credentials redirects to `/dashboard`.
- [ ] Dashboard shows the correct balance and username.
- [ ] Navigating directly to `/deposit` without being logged in redirects to `/login`.
- [ ] Depositing a valid amount updates the balance on the dashboard immediately.
- [ ] Depositing zero or a negative number shows a validation error.
- [ ] Withdrawing more than the available balance shows "Insufficient funds".
- [ ] Withdrawing a valid amount updates the balance correctly.
- [ ] Clicking Logout redirects to `/login` and clears the session (browser back button cannot return to dashboard).
- [ ] All pages display correctly on a mobile-width browser window (Bootstrap responsiveness).

---

## 7. Deployment

### 7.1 Run Locally
1. Activate the virtual environment inside the `BACKEND` folder.
2. Run `flask run` — Flask will start a development server at `http://127.0.0.1:5000`.
3. Open that URL in your browser and log in with the seeded credentials.

> **Note:** Flask's built-in development server is single-threaded and not suitable for production. It should only be used for local development and testing.

To change the port, set the `FLASK_RUN_PORT` environment variable before running. To enable debug mode (auto-reload on code changes and an interactive debugger), set `FLASK_DEBUG=1` — but **never enable debug mode in production**.

### 7.2 Production Considerations

| Concern | Recommendation |
|---|---|
| **WSGI server** | Replace `flask run` with a production WSGI server such as **Gunicorn** or **Waitress**. These handle concurrent requests correctly and are stable under load. |
| **Reverse proxy** | Place **Nginx** or **Apache** in front of Gunicorn. The proxy handles HTTPS termination, static file serving, and rate limiting. |
| **HTTPS / TLS** | Obtain a TLS certificate (Let's Encrypt is free) and configure Nginx to redirect all HTTP traffic to HTTPS. Flask sessions are cookie-based and must be protected in transit. |
| **Secret key** | Store the Flask `SECRET_KEY` in an environment variable or a secrets manager — never hardcode it in `app.py`. |
| **Database** | SQLite is acceptable for very low-traffic deployments. For anything beyond a single server, migrate to **PostgreSQL** or **MySQL** using SQLAlchemy as the ORM layer. |
| **Password storage** | Already handled by Werkzeug's `generate_password_hash` — ensure the hashing algorithm is set to `scrypt` or `pbkdf2:sha256` with a high iteration count. |
| **Session security** | Set `SESSION_COOKIE_SECURE = True` (HTTPS only), `SESSION_COOKIE_HTTPONLY = True` (no JavaScript access), and `SESSION_COOKIE_SAMESITE = 'Lax'` to mitigate CSRF and XSS risks. |
| **Logging** | Configure Python's `logging` module to write request errors and exceptions to a file. Avoid logging sensitive fields such as passwords or full session tokens. |
| **Environment variables** | Use a `.env` file (loaded by `python-dotenv`) locally. On a server, set variables directly in the system environment or via your hosting platform's secrets feature. |

---

*This guide describes implementation logic in plain English. For the actual code, refer to the source files in the `BACKEND/` and `FRONTEND/` folders as they are built out.*
