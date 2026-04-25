"""
database.py — All SQLite3 operations for the E-Banking platform.
"""
import sqlite3
import random
import string
from werkzeug.security import generate_password_hash

DATABASE = 'ebanking.db'


# ─────────────────────────────── connection ───────────────────────────────

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # prevent 'database is locked'
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    with open('schema.sql', 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


# ─────────────────────────────── utilities ────────────────────────────────

def generate_account_number():
    """Generate a unique DZ account number."""
    while True:
        number = 'TN' + ''.join(random.choices(string.digits, k=12))
        conn = get_db()
        exists = conn.execute(
            'SELECT id FROM accounts WHERE account_number = ?', (number,)
        ).fetchone()
        conn.close()
        if not exists:
            return number


# ─────────────────────────────── users ────────────────────────────────────

def get_user(user_id):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return user


def get_user_by_email(email):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user


def create_user(full_name, email, password_hash, role, phone='', address=''):
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO users (full_name, email, password_hash, role, phone, address) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (full_name, email, password_hash, role, phone, address)
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_all_users():
    conn = get_db()
    users = conn.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return users


def toggle_user_status(user_id, status):
    conn = get_db()
    conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (status, user_id))
    
    # Option B: Synchronize account status with user status
    if status == 0:
        # Freeze active accounts when user is deactivated
        conn.execute("UPDATE accounts SET status = 'frozen' WHERE user_id = ? AND status = 'active'", (user_id,))
    else:
        # Reactivate frozen accounts when user is activated
        conn.execute("UPDATE accounts SET status = 'active' WHERE user_id = ? AND status = 'frozen'", (user_id,))
        
    conn.commit()
    conn.close()


def delete_user(user_id):
    """Delete a user and all their related data.
    We manually delete in order to handle FK constraints that lack CASCADE:
    loan_requests → accounts → users, and transactions referencing accounts.
    """
    conn = get_db()
    try:
        # 1. Get all account IDs for this user
        account_ids = [
            row[0] for row in
            conn.execute('SELECT id FROM accounts WHERE user_id = ?', (user_id,)).fetchall()
        ]

        # 2. Delete transactions that reference these accounts
        if account_ids:
            placeholders = ','.join('?' * len(account_ids))
            conn.execute(
                f'DELETE FROM transactions WHERE from_account_id IN ({placeholders}) '
                f'OR to_account_id IN ({placeholders})',
                account_ids + account_ids
            )

        # 3. Delete loan_requests for this user
        conn.execute('DELETE FROM loan_requests WHERE user_id = ?', (user_id,))

        # 4. Delete notifications for this user
        conn.execute('DELETE FROM notifications WHERE user_id = ?', (user_id,))

        # 5. Delete audit_logs for this user
        conn.execute('UPDATE audit_logs SET user_id = NULL WHERE user_id = ?', (user_id,))

        # 6. Delete accounts (now no transactions reference them)
        conn.execute('DELETE FROM accounts WHERE user_id = ?', (user_id,))

        # 7. Finally delete the user
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_user_info(user_id, full_name, phone, address):
    conn = get_db()
    conn.execute(
        'UPDATE users SET full_name = ?, phone = ?, address = ? WHERE id = ?',
        (full_name, phone, address, user_id)
    )
    conn.commit()
    conn.close()


def update_password(user_id, password_hash):
    conn = get_db()
    conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
    conn.close()


# ─────────────────────────────── accounts ─────────────────────────────────

def create_account(user_id, account_number, account_type, balance=0.0):
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO accounts (user_id, account_number, account_type, balance) '
        'VALUES (?, ?, ?, ?)',
        (user_id, account_number, account_type, balance)
    )
    acc_id = cur.lastrowid
    conn.commit()
    conn.close()
    return acc_id


def get_account(account_id):
    conn = get_db()
    acc = conn.execute('SELECT * FROM accounts WHERE id = ?', (account_id,)).fetchone()
    conn.close()
    return acc


def get_account_by_number(account_number):
    conn = get_db()
    acc = conn.execute(
        'SELECT * FROM accounts WHERE account_number = ?', (account_number,)
    ).fetchone()
    conn.close()
    return acc


def get_user_accounts(user_id):
    conn = get_db()
    accs = conn.execute(
        'SELECT * FROM accounts WHERE user_id = ? ORDER BY created_at', (user_id,)
    ).fetchall()
    conn.close()
    return accs


def get_all_accounts_with_users():
    conn = get_db()
    accs = conn.execute('''
        SELECT a.*, u.full_name, u.email
        FROM accounts a
        JOIN users u ON a.user_id = u.id
        ORDER BY a.created_at DESC
    ''').fetchall()
    conn.close()
    return accs


def update_account_balance(account_id, delta):
    conn = get_db()
    conn.execute(
        'UPDATE accounts SET balance = balance + ? WHERE id = ?', (delta, account_id)
    )
    conn.commit()
    conn.close()


def update_account_status(account_id, status):
    conn = get_db()
    conn.execute('UPDATE accounts SET status = ? WHERE id = ?', (status, account_id))
    conn.commit()
    conn.close()


# ─────────────────────────────── transactions ─────────────────────────────

def create_transaction(from_account_id, to_account_id, amount,
                       tx_type, description='', status='pending'):
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO transactions '
        '(from_account_id, to_account_id, amount, type, description, status) '
        'VALUES (?, ?, ?, ?, ?, ?)',
        (from_account_id, to_account_id, amount, tx_type, description, status)
    )
    tx_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tx_id


def get_transaction(tx_id):
    conn = get_db()
    tx = conn.execute('SELECT * FROM transactions WHERE id = ?', (tx_id,)).fetchone()
    conn.close()
    return tx


def get_pending_transactions():
    conn = get_db()
    txs = conn.execute('''
        SELECT t.*,
               fa.account_number AS from_number,
               fa.user_id        AS from_user_id,
               ta.account_number AS to_number,
               u.full_name       AS from_name
        FROM   transactions t
        LEFT JOIN accounts fa ON t.from_account_id = fa.id
        LEFT JOIN accounts ta ON t.to_account_id   = ta.id
        LEFT JOIN users    u  ON fa.user_id         = u.id
        WHERE  t.status = 'pending'
        ORDER  BY t.created_at DESC
    ''').fetchall()
    conn.close()
    return txs


def get_user_transactions(user_id, limit=None, tx_type='', status=''):
    conn = get_db()
    query = '''
        SELECT t.*,
               fa.account_number AS from_number,
               ta.account_number AS to_number,
               fu.full_name      AS from_name,
               tu.full_name      AS to_name
        FROM   transactions t
        LEFT JOIN accounts fa ON t.from_account_id = fa.id
        LEFT JOIN accounts ta ON t.to_account_id   = ta.id
        LEFT JOIN users    fu ON fa.user_id         = fu.id
        LEFT JOIN users    tu ON ta.user_id         = tu.id
        WHERE  (fa.user_id = ? OR ta.user_id = ?)
    '''
    params = [user_id, user_id]
    if tx_type:
        query += ' AND t.type = ?'
        params.append(tx_type)
    if status:
        query += ' AND t.status = ?'
        params.append(status)
    query += ' ORDER BY t.created_at DESC'
    if limit:
        query += f' LIMIT {int(limit)}'
    txs = conn.execute(query, params).fetchall()
    conn.close()
    return txs


def get_all_transactions(status=''):
    conn = get_db()
    query = '''
        SELECT t.*,
               fa.account_number AS from_number,
               ta.account_number AS to_number,
               fu.full_name      AS from_name,
               tu.full_name      AS to_name
        FROM   transactions t
        LEFT JOIN accounts fa ON t.from_account_id = fa.id
        LEFT JOIN accounts ta ON t.to_account_id   = ta.id
        LEFT JOIN users    fu ON fa.user_id         = fu.id
        LEFT JOIN users    tu ON ta.user_id         = tu.id
    '''
    params = []
    if status:
        query += ' WHERE t.status = ?'
        params.append(status)
    query += ' ORDER BY t.created_at DESC'
    txs = conn.execute(query, params).fetchall()
    conn.close()
    return txs


def update_transaction_status(tx_id, status, reviewed_by=None):
    conn = get_db()
    conn.execute(
        'UPDATE transactions SET status = ?, reviewed_by = ?, '
        'reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
        (status, reviewed_by, tx_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────── loans ────────────────────────────────────

def create_loan_request(user_id, amount, duration_months, purpose):
    conn = get_db()
    cur = conn.execute(
        'INSERT INTO loan_requests (user_id, amount, duration_months, purpose) '
        'VALUES (?, ?, ?, ?)',
        (user_id, amount, duration_months, purpose)
    )
    loan_id = cur.lastrowid
    conn.commit()
    conn.close()
    return loan_id


def get_loan(loan_id):
    conn = get_db()
    loan = conn.execute('''
        SELECT l.*, u.full_name, u.email
        FROM   loan_requests l
        JOIN   users u ON l.user_id = u.id
        WHERE  l.id = ?
    ''', (loan_id,)).fetchone()
    conn.close()
    return loan


def get_user_loans(user_id):
    conn = get_db()
    loans = conn.execute(
        'SELECT * FROM loan_requests WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return loans


def get_all_loans():
    conn = get_db()
    loans = conn.execute('''
        SELECT l.*, u.full_name, u.email
        FROM   loan_requests l
        JOIN   users u ON l.user_id = u.id
        ORDER  BY l.created_at DESC
    ''').fetchall()
    conn.close()
    return loans


def update_loan_status(loan_id, status, reviewed_by, comment=''):
    conn = get_db()
    conn.execute(
        'UPDATE loan_requests SET status = ?, reviewed_by = ?, comment = ?, '
        'reviewed_at = CURRENT_TIMESTAMP WHERE id = ?',
        (status, reviewed_by, comment, loan_id)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────── notifications ────────────────────────────

def add_notification(user_id, title, message):
    conn = get_db()
    conn.execute(
        'INSERT INTO notifications (user_id, title, message) VALUES (?, ?, ?)',
        (user_id, title, message)
    )
    conn.commit()
    conn.close()


def get_unread_notifications(user_id):
    conn = get_db()
    notifs = conn.execute(
        'SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 '
        'ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()
    conn.close()
    return notifs


def get_unread_notification_count(user_id):
    conn = get_db()
    count = conn.execute(
        'SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0',
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def mark_all_notifications_read(user_id):
    conn = get_db()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────── audit logs ───────────────────────────────

def add_audit_log(user_id, action, details='', ip_address=''):
    conn = get_db()
    conn.execute(
        'INSERT INTO audit_logs (user_id, action, details, ip_address) '
        'VALUES (?, ?, ?, ?)',
        (user_id, action, details, ip_address)
    )
    conn.commit()
    conn.close()


def get_audit_logs(limit=300):
    conn = get_db()
    logs = conn.execute('''
        SELECT l.*, u.full_name, u.email
        FROM   audit_logs l
        LEFT JOIN users u ON l.user_id = u.id
        ORDER  BY l.created_at DESC
        LIMIT  ?
    ''', (limit,)).fetchall()
    conn.close()
    return logs


# ─────────────────────────────── stats ────────────────────────────────────

def get_admin_stats():
    conn = get_db()
    s = {}
    s['total_customers']        = conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0]
    s['total_gestionnaires']    = conn.execute("SELECT COUNT(*) FROM users WHERE role='gestionnaire'").fetchone()[0]
    s['total_accounts']         = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    s['total_balance']          = conn.execute("SELECT COALESCE(SUM(balance),0) FROM accounts").fetchone()[0]
    s['pending_transactions']   = conn.execute("SELECT COUNT(*) FROM transactions WHERE status='pending'").fetchone()[0]
    s['completed_transactions'] = conn.execute("SELECT COUNT(*) FROM transactions WHERE status='completed'").fetchone()[0]
    s['pending_loans']          = conn.execute("SELECT COUNT(*) FROM loan_requests WHERE status='pending'").fetchone()[0]
    s['active_accounts']        = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='active'").fetchone()[0]
    s['frozen_accounts']        = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='frozen'").fetchone()[0]
    s['closed_accounts']        = conn.execute("SELECT COUNT(*) FROM accounts WHERE status='closed'").fetchone()[0]
    conn.close()
    return s


def get_gestionnaire_stats():
    conn = get_db()
    s = {}
    s['pending_transfers'] = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE status='pending'"
    ).fetchone()[0]
    s['approved_today'] = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE status='completed' "
        "AND date(reviewed_at)=date('now')"
    ).fetchone()[0]
    s['rejected_today'] = conn.execute(
        "SELECT COUNT(*) FROM transactions WHERE status='rejected' "
        "AND date(reviewed_at)=date('now')"
    ).fetchone()[0]
    s['pending_loans'] = conn.execute(
        "SELECT COUNT(*) FROM loan_requests WHERE status='pending'"
    ).fetchone()[0]
    conn.close()
    return s


def get_monthly_stats():
    import datetime
    
    # Generate the last 6 months in 'YYYY-MM' format using only stdlib
    today = datetime.date.today()
    months = []
    
    current_year = today.year
    current_month = today.month
    
    for _ in range(6):
        months.append(f"{current_year}-{current_month:02d}")
        current_month -= 1
        if current_month == 0:
            current_month = 12
            current_year -= 1
            
    # Reverse to have oldest first for building the list, 
    # but we will just keep them and the dashboard reverses them back, 
    # so let's stick to the order: we want [current, current-1, ..., current-5]
    # then we reverse it at the end to return [current-5, ..., current]
    months = months[::-1]
        
    conn = get_db()
    rows = conn.execute('''
        SELECT strftime('%Y-%m', created_at) AS month,
               SUM(amount) AS total,
               COUNT(*)    AS count
        FROM   transactions
        WHERE  status = 'completed'
        GROUP  BY month
    ''').fetchall()
    conn.close()
    
    # Create a dictionary for quick lookup
    db_data = {r['month']: {'total': r['total'] or 0, 'count': r['count']} for r in rows}
    
    # Build the final synchronized list
    result = []
    for m in months:
        if m in db_data:
            result.append({'month': m, 'total': db_data[m]['total'], 'count': db_data[m]['count']})
        else:
            result.append({'month': m, 'total': 0, 'count': 0})
            
    # Reverse to match the dashboard's expected order (newest first)
    return result[::-1]


# ─────────────────────────────── seed data ────────────────────────────────

def seed_demo_data():
    conn = get_db()
    existing = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    if existing > 0:
        return  # already seeded

    # Staff
    admin_id = create_user('Admin Système',       'admin@ebank.tn',
                           generate_password_hash('admin123'),
                           'admin', '+216 71 000 001', 'Avenue Habib Bourguiba, Tunis')
    gest_id  = create_user('Karim Gestionnaire',  'gestionnaire@ebank.tn',
                           generate_password_hash('gest123'),
                           'gestionnaire', '+216 74 000 002', 'Avenue Farhat Hached, Sfax')

    # Customers
    c1 = create_user('Youssef Ben Salem', 'youssef@gmail.com',
                     generate_password_hash('client123'), 'customer',
                     '+216 20 111 111', '12 Avenue Habib Bourguiba, Tunis')
    c2 = create_user('Amina Trabelsi',   'amina@gmail.com',
                     generate_password_hash('client123'), 'customer',
                     '+216 25 222 222', '5 Rue de Carthage, Sousse')
    c3 = create_user('Mehdi Jebali',     'mehdi@gmail.com',
                     generate_password_hash('client123'), 'customer',
                     '+216 98 333 333', '8 Avenue de la République, Sfax')

    # Accounts
    a1 = create_account(c1, generate_account_number(), 'courant',  125_000.00)
    a2 = create_account(c1, generate_account_number(), 'epargne',  350_000.00)
    a3 = create_account(c2, generate_account_number(), 'courant',   87_500.50)
    a4 = create_account(c3, generate_account_number(), 'courant',   45_200.00)
    a5 = create_account(c3, generate_account_number(), 'epargne',  220_000.00)

    # Transactions
    create_transaction(a1, a3, 15_000, 'virement', 'Remboursement loyer',   'completed')
    create_transaction(a3, a1,  5_000, 'virement', 'Achat en ligne',        'completed')
    create_transaction(a2, a4, 20_000, 'virement', 'Salaire freelance',     'completed')
    create_transaction(a1, a4,  8_000, 'virement', 'Transfert en attente',  'pending')
    create_transaction(a4, a3,  3_500, 'virement', 'Transfert rejeté',      'rejected')
    create_transaction(None, a1, 50_000, 'depot',  'Dépôt initial',         'completed')
    create_transaction(None, a3, 30_000, 'depot',  'Dépôt initial',         'completed')
    create_transaction(None, a5, 10_000, 'depot',  'Dépôt épargne',         'completed')

    # Loans
    create_loan_request(c2, 500_000,  60,  'Achat véhicule')
    create_loan_request(c3, 1_200_000, 120, 'Construction maison')

    # Notifications
    for uid, name in [(c1, 'Youssef'), (c2, 'Amina'), (c3, 'Mehdi')]:
        add_notification(uid, 'Bienvenue sur Secure e-Bank !',
                         f'Bonjour {name}, votre compte est prêt.')

    add_notification(c1, 'Virement reçu', '15 000 DNT reçus de Amina Cherif.')
    add_notification(c2, 'Demande de prêt', 'Votre demande de prêt est en cours d\'examen.')

    # Audit
    add_audit_log(admin_id, 'SYSTEM_INIT', 'Base initialisée avec données de démo', '127.0.0.1')

    print('\n[OK]  Demo data loaded!')
    print('   admin@ebank.tn         / admin123')
    print('   gestionnaire@ebank.tn  / gest123')
    print('   youssef@gmail.com      / client123')
    print('   amina@gmail.com        / client123')
    print('   mehdi@gmail.com        / client123\n')
