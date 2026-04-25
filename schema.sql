-- ============================================================
--  E-Banking Platform — SQLite3 Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT    NOT NULL,
    email           TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'customer'
                            CHECK(role IN ('customer','gestionnaire','admin')),
    is_active       INTEGER NOT NULL DEFAULT 1,
    phone           TEXT    DEFAULT '',
    address         TEXT    DEFAULT '',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    account_number  TEXT    UNIQUE NOT NULL,
    account_type    TEXT    NOT NULL DEFAULT 'courant'
                            CHECK(account_type IN ('courant','epargne')),
    balance         REAL    NOT NULL DEFAULT 0.0,
    currency        TEXT    NOT NULL DEFAULT 'DNT',
    status          TEXT    NOT NULL DEFAULT 'active'
                            CHECK(status IN ('active','frozen','closed')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    from_account_id  INTEGER,
    to_account_id    INTEGER,
    amount           REAL    NOT NULL,
    type             TEXT    NOT NULL
                             CHECK(type IN ('virement','depot','retrait')),
    status           TEXT    NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending','completed','rejected')),
    description      TEXT    DEFAULT '',
    reviewed_by      INTEGER,
    reviewed_at      TIMESTAMP,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_account_id) REFERENCES accounts(id),
    FOREIGN KEY (to_account_id)   REFERENCES accounts(id),
    FOREIGN KEY (reviewed_by)     REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS loan_requests (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    amount           REAL    NOT NULL,
    duration_months  INTEGER NOT NULL,
    purpose          TEXT    DEFAULT '',
    status           TEXT    NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending','approved','rejected')),
    reviewed_by      INTEGER,
    comment          TEXT    DEFAULT '',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at      TIMESTAMP,
    FOREIGN KEY (user_id)     REFERENCES users(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS notifications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    action      TEXT    NOT NULL,
    details     TEXT    DEFAULT '',
    ip_address  TEXT    DEFAULT '',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
