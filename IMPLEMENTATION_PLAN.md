# Banking Web Application — Implementation Plan

---

## 1. Solution Overview

### Objective
Build a lightweight browser-based banking application that allows customers to log in, view their account balance, deposit and withdraw funds, and securely log out.

### Scope
| In Scope | Out of Scope |
|---|---|
| Customer login / logout | Admin portal |
| View account balance | Multi-currency support |
| Deposit & withdrawal transactions | Inter-account transfers |
| Session-based authentication | Third-party payment integration |
| Responsive UI via Bootstrap | SMS / email notifications |

### Users
- **Customer** — a single user role. Each customer has one account and can perform all in-scope actions after authenticating.

### Functional Requirements
1. A customer can log in with a username and password.
2. After login, the customer sees a dashboard summarising their account balance.
3. The customer can deposit a positive amount; the balance updates immediately.
4. The customer can withdraw a positive amount up to the available balance.
5. The customer can log out, which terminates the session.

### Non-Functional Requirements
- **Security** — passwords stored as hashed values; sessions expire on logout.
- **Usability** — all pages are responsive and functional on modern desktop browsers.
- **Simplicity** — no build pipeline; the backend serves HTML templates directly.
- **Portability** — runs locally with a single `flask run` command and no external services.

### Assumptions
- SQLite is sufficient for a single-node, low-concurrency deployment.
- Bootstrap is loaded from CDN; no local asset compilation is required.
- A single customer account may be pre-seeded for demonstration purposes.
- HTTPS termination is out of scope (development environment only).

---

## 2. High-Level Architecture

### Architecture Diagram

```
┌─────────────────────────────────┐
│           BROWSER               │
│  Bootstrap HTML pages           │
│  Form submissions / fetch calls │
└────────────┬────────────────────┘
             │  HTTP (GET / POST)
             ▼
┌─────────────────────────────────┐
│         FLASK BACKEND           │
│  Route handlers (views)         │
│  Session management             │
│  Business logic                 │
│  Jinja2 templates               │
└────────────┬────────────────────┘
             │  SQL queries via sqlite3 / SQLAlchemy
             ▼
┌─────────────────────────────────┐
│         SQLITE DATABASE         │
│  Persistent storage             │
│  users, accounts, transactions  │
└─────────────────────────────────┘
```

### Frontend → Backend → Database Interaction
- The **frontend** renders HTML pages that include Bootstrap-styled forms and navigation.
- Each user action (login, deposit, withdraw, logout) submits an HTTP POST or GET request to a Flask route.
- **Flask** validates the request, applies business rules, reads or writes to **SQLite**, and returns a rendered template or redirect.

### Request Lifecycle

```
Browser submits form
        │
        ▼
Flask route receives request
        │
        ├─► Validate session (is user logged in?)
        │
        ├─► Validate input (amount > 0, sufficient balance, etc.)
        │
        ├─► Execute database read / write
        │
        └─► Return rendered template (success) or error page / flash message
```

---

## 3. Component Design

### Frontend Responsibilities
- Render login form and capture credentials.
- Display dashboard with current balance and action buttons.
- Provide deposit and withdrawal forms with basic client-side input constraints.
- Display server-side flash messages (success, error).
- Implement navigation bar with active logout link.
- All pages use Bootstrap grid and components for consistent, responsive layout.

### Backend Responsibilities
- Serve all HTML via Jinja2 templates.
- Authenticate users against hashed passwords stored in the database.
- Manage user sessions (create on login, destroy on logout).
- Enforce business rules: positive amounts, sufficient balance before withdrawal.
- Perform all database reads and writes; never expose raw data directly to templates beyond what is needed.
- Protect all non-login routes with a login-required guard.

### Database Responsibilities
- Persist user credentials (username + password hash).
- Persist account records linked to users (balance).
- Persist a transaction log (type, amount, timestamp) for auditability.
- Provide ACID guarantees for balance updates to avoid lost updates on concurrent requests.

---

## 4. Folder Structure

```
project-root/
│
├── FRONTEND/
│   └── templates/               # Jinja2 HTML templates
│       ├── base.html            # Shared layout, Bootstrap CDN, nav bar
│       ├── login.html           # Login form
│       ├── dashboard.html       # Balance overview + action links
│       ├── deposit.html         # Deposit form
│       ├── withdraw.html        # Withdrawal form
│       └── (partials/macros)    # Optional reusable snippets
│
├── BACKEND/
│   ├── app.py                   # Flask application factory & route definitions
│   ├── auth.py                  # Login, logout, session helpers
│   ├── accounts.py              # Balance query, deposit, withdraw logic
│   ├── db.py                    # Database connection & initialisation helper
│   ├── models.py                # Data model definitions (ORM or dataclasses)
│   ├── banking.db               # SQLite database file (auto-created at runtime)
│   └── requirements.txt         # Python dependencies (flask, etc.)
│
└── IMPLEMENTATION_PLAN.md       # This document
```

### Folder Responsibilities

| Path | Responsibility |
|---|---|
| `FRONTEND/templates/` | All user-facing HTML. No business logic — only layout, form fields, and template variables. |
| `BACKEND/app.py` | Entry point. Registers blueprints/routes, configures Flask app and secret key. |
| `BACKEND/auth.py` | Authentication logic: password hashing, session creation/destruction, login-required decorator. |
| `BACKEND/accounts.py` | Account operations: read balance, apply deposit, apply withdrawal with validation. |
| `BACKEND/db.py` | Opens SQLite connection, runs schema initialisation, exposes a `get_db()` helper. |
| `BACKEND/models.py` | Defines the shape of User, Account, and Transaction data (dataclasses or SQLAlchemy models). |
| `BACKEND/banking.db` | Auto-generated SQLite file; not committed to version control. |

---

## 5. Module Breakdown

### Authentication Module
**Files:** `auth.py`, `login.html`
- Handles `POST /login` — validates credentials, creates session.
- Handles `GET /logout` — clears session, redirects to login.
- Provides a `login_required` decorator used by all protected routes.
- Password comparison uses a constant-time hash check to prevent timing attacks.

### Dashboard Module
**Files:** `app.py` (route), `dashboard.html`
- Handles `GET /dashboard` — retrieves current balance for logged-in user and renders summary.
- Acts as the post-login landing page.
- Displays flash messages from previous actions (deposit success, error, etc.).

### Account Management Module
**Files:** `accounts.py`, `models.py`, `db.py`
- Provides `get_balance(user_id)` — queries current account balance.
- Provides `get_transactions(user_id)` — retrieves recent transaction history (optional display on dashboard).
- Encapsulates all direct database interaction for account data.

### Transactions Module
**Files:** `accounts.py`, `deposit.html`, `withdraw.html`
- Handles `POST /deposit` — validates amount, increments balance, writes transaction record.
- Handles `POST /withdraw` — validates amount and sufficient balance, decrements balance, writes transaction record.
- Both operations are wrapped in a database transaction to ensure atomicity.

---

## 6. Implementation Roadmap

### Development Phases

#### Phase 1 — Project Scaffolding
Set up the folder structure, Flask app skeleton, and SQLite initialisation. Confirm the application starts without errors.

**Dependencies:** None
**Effort:** Low

#### Phase 2 — Database Layer
Define the schema (users, accounts, transactions) and implement `db.py` and `models.py`. Seed one test customer account.

**Dependencies:** Phase 1
**Effort:** Low

#### Phase 3 — Authentication
Implement login and logout routes, password hashing, session management, and the `login_required` guard. Build `login.html`.

**Dependencies:** Phase 2
**Effort:** Medium

#### Phase 4 — Dashboard
Implement the `/dashboard` route to fetch and display account balance. Build `dashboard.html` with Bootstrap layout.

**Dependencies:** Phase 3
**Effort:** Low

#### Phase 5 — Deposit & Withdrawal
Implement the deposit and withdrawal routes with input validation and atomic balance updates. Build `deposit.html` and `withdraw.html`.

**Dependencies:** Phase 4
**Effort:** Medium

#### Phase 6 — UI Polish & Integration Testing
Apply consistent Bootstrap styling across all templates. Test the full login → dashboard → transaction → logout flow end-to-end.

**Dependencies:** Phase 5
**Effort:** Low–Medium

### Dependency Chain

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
```

Phases 4 and 5 can be partially parallelised (template build vs. route logic) but the route for Phase 5 depends on Phase 4's session guard being in place.

---

*This document is a planning-level specification. No SQL scripts, API contracts, or implementation code are included.*
