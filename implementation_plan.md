# E-Banking Platform — Full Stack Implementation Plan

## Overview
A dynamic, multi-role e-banking web application built with **Flask + SQLite3** on the backend and **HTML / CSS / JS** on the frontend. Three distinct user roles each get a tailored portal with a premium dark-themed UI.

---

## User Roles & Portals

| Role | Description |
|---|---|
| **Customer** | Registers, logs in, manages personal accounts, makes transfers, views history, requests loans |
| **Gestionnaire** (Manager) | Reviews & approves/rejects customer operations and loan requests |
| **Admin** | Full system control — manages users, accounts, sees all analytics |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python · Flask · Flask-Login · Werkzeug (password hashing) |
| Database | SQLite3 (via `sqlite3` stdlib) |
| Frontend | HTML5 · Vanilla CSS (dark glassmorphism theme) · Vanilla JS |
| Auth | Flask sessions with role-based access control |

---

## Database Schema

### `users`
```
id, full_name, email, password_hash, role (customer/gestionnaire/admin),
is_active, created_at
```

### `accounts`
```
id, user_id, account_number (auto-generated), account_type (courant/epargne),
balance, currency (DZD), status (active/frozen/closed), created_at
```

### `transactions`
```
id, from_account_id, to_account_id, amount, type (virement/depot/retrait),
status (pending/approved/rejected/completed), description, created_at
```

### `loan_requests`
```
id, user_id, amount, duration_months, purpose, status (pending/approved/rejected),
reviewed_by, created_at, reviewed_at
```

### `notifications`
```
id, user_id, title, message, is_read, created_at
```

### `audit_logs`
```
id, user_id, action, details, ip_address, created_at
```

---

## Project Structure

```
big proj/
├── app.py                   # Flask entry point & routes
├── database.py              # DB init & helper functions
├── schema.sql               # SQLite schema
├── requirements.txt
├── static/
│   ├── css/
│   │   ├── main.css         # Shared design system (dark glassmorphism)
│   │   ├── auth.css         # Login / Register pages
│   │   ├── customer.css     # Customer portal
│   │   ├── gestionnaire.css # Gestionnaire portal
│   │   └── admin.css        # Admin portal
│   ├── js/
│   │   ├── main.js          # Shared utilities
│   │   ├── dashboard.js     # Charts & live data
│   │   └── transfer.js      # Transfer form validation
│   └── img/
│       └── logo.svg
└── templates/
    ├── base.html            # Shared layout (nav, flash messages)
    ├── index.html           # Landing page
    ├── auth/
    │   ├── login.html
    │   └── register.html
    ├── customer/
    │   ├── dashboard.html
    │   ├── accounts.html
    │   ├── transfer.html
    │   ├── history.html
    │   ├── loans.html
    │   └── profile.html
    ├── gestionnaire/
    │   ├── dashboard.html
    │   ├── pending.html
    │   ├── loans.html
    │   └── accounts.html
    └── admin/
        ├── dashboard.html
        ├── users.html
        ├── accounts.html
        ├── transactions.html
        └── logs.html
```

---

## Key Features Per Role

### 🏠 Landing Page (`/`)
- Hero section with animated banking illustration
- Features overview
- "Sign In" / "Register" CTAs

### 👤 Customer Portal (`/customer/...`)
- **Dashboard** — balance cards, recent transactions, quick actions
- **Accounts** — view all linked accounts with status badges
- **Transfer** — send money (internal or by account number), with real-time validation
- **History** — paginated transaction log with filters (date, type, status)
- **Loans** — request new loan, track existing requests
- **Profile** — update personal info, change password

### 🗂️ Gestionnaire Portal (`/gestionnaire/...`)
- **Dashboard** — stats (pending operations, approved today, rejected today)
- **Pending Transfers** — approve / reject with optional comment
- **Loan Requests** — review and decide with reason
- **Customer Accounts** — view details, freeze/unfreeze account

### ⚙️ Admin Portal (`/admin/...`)
- **Dashboard** — system-wide KPI cards + Chart.js graphs
- **User Management** — create / edit / deactivate users of any role
- **Account Management** — full account CRUD
- **All Transactions** — filter, search, export CSV
- **Audit Logs** — track every admin/gestionnaire action

---

## Design System — Dark Glassmorphism

- **Background**: `#0a0e1a` (deep navy)
- **Cards**: `rgba(255,255,255,0.05)` + `backdrop-filter: blur`
- **Accent**: `#3d9ef5` (electric blue) + `#00d4aa` (teal)
- **Danger**: `#ff4d6d`
- **Font**: `Inter` (Google Fonts)
- **Animations**: smooth sidebar transitions, card hover lifts, chart reveals

---

## Proposed Changes

### [NEW] `requirements.txt`
### [NEW] `schema.sql`
### [NEW] `database.py`
### [NEW] `app.py` (Flask routes, auth, RBAC decorators)
### [NEW] `static/css/main.css`
### [NEW] `static/css/auth.css`
### [NEW] `static/css/customer.css`
### [NEW] `static/css/gestionnaire.css`
### [NEW] `static/css/admin.css`
### [NEW] `static/js/main.js` + `dashboard.js` + `transfer.js`
### [NEW] All 15+ HTML templates

---

## Verification Plan

### Automated Seed
- `database.py` will include a `seed_demo_data()` function with:
  - 1 admin, 1 gestionnaire, 3 customers
  - Pre-seeded accounts & transaction history

### Manual Browser Testing
- Login as each role and verify portal access
- Attempt cross-role URL access (must redirect/403)
- Complete a full transfer flow: customer → pending → gestionnaire approval
- Submit & approve a loan request
- Admin creates new user & freezes an account

---

## Implementation Order
1. `schema.sql` + `database.py`
2. `app.py` (auth + RBAC)
3. CSS design system
4. Landing + auth templates
5. Customer portal (5 pages)
6. Gestionnaire portal (4 pages)
7. Admin portal (5 pages)
8. JS interactivity & charts
9. Seed data & test
