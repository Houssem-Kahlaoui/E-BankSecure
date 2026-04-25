"""
app.py — Flask E-Banking application entry point.
"""
import os
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, jsonify)
from werkzeug.security import generate_password_hash, check_password_hash
import database as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ebanking-super-secret-Secure e-Bank-2024')


# ────────────────────────── context processor ─────────────────────────────

@app.context_processor
def inject_globals():
    count = 0
    if session.get('user_id') and session.get('role') == 'customer':
        count = db.get_unread_notification_count(session['user_id'])
    return {'notifications_count': count}


# ────────────────────────── decorators ────────────────────────────────────

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('home_redirect'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ────────────────────────── redirect helper ───────────────────────────────

@app.route('/home')
def home_redirect():
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    if role == 'gestionnaire':
        return redirect(url_for('gestionnaire_dashboard'))
    if role == 'customer':
        return redirect(url_for('customer_dashboard'))
    return redirect(url_for('landing'))


# ════════════════════════════════════════════════════════════════════════════
#  LANDING
# ════════════════════════════════════════════════════════════════════════════

@app.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('home_redirect'))
    return render_template('index.html')


# ════════════════════════════════════════════════════════════════════════════
#  AUTH
# ════════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home_redirect'))
    if request.method == 'POST':
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user     = db.get_user_by_email(email)
        if user and check_password_hash(user['password_hash'], password):
            if not user['is_active']:
                flash('Votre compte est désactivé. Contactez l\'administrateur.', 'danger')
                return render_template('auth/login.html')
            session.clear()
            session['user_id']   = user['id']
            session['role']      = user['role']
            session['full_name'] = user['full_name']
            session['email']     = user['email']
            db.add_audit_log(user['id'], 'LOGIN', 'Connexion réussie', request.remote_addr)
            flash(f'Bienvenue, {user["full_name"]} !', 'success')
            return redirect(url_for('home_redirect'))
        flash('Email ou mot de passe incorrect.', 'danger')
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home_redirect'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email     = request.form.get('email', '').strip()
        phone     = request.form.get('phone', '').strip()
        address   = request.form.get('address', '').strip()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')

        if not all([full_name, email, password, confirm]):
            flash('Veuillez remplir tous les champs obligatoires.', 'warning')
            return render_template('auth/register.html')
        if password != confirm:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('auth/register.html')
        if len(password) < 6:
            flash('Le mot de passe doit contenir au moins 6 caractères.', 'danger')
            return render_template('auth/register.html')
        if db.get_user_by_email(email):
            flash('Cet email est déjà utilisé.', 'danger')
            return render_template('auth/register.html')

        pw_hash  = generate_password_hash(password)
        user_id  = db.create_user(full_name, email, pw_hash, 'customer', phone, address)
        acc_num  = db.generate_account_number()
        db.create_account(user_id, acc_num, 'courant', 0.0)
        db.add_notification(user_id, 'Bienvenue sur Secure e-Bank !',
                            f'Votre compte courant {acc_num} a été créé.')
        flash('Compte créé ! Vous pouvez maintenant vous connecter.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        db.add_audit_log(session['user_id'], 'LOGOUT', 'Déconnexion', request.remote_addr)
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('landing'))


# ════════════════════════════════════════════════════════════════════════════
#  CUSTOMER
# ════════════════════════════════════════════════════════════════════════════

@app.route('/customer/dashboard')
@login_required
@role_required('customer')
def customer_dashboard():
    user          = db.get_user(session['user_id'])
    accounts      = db.get_user_accounts(session['user_id'])
    recent_tx     = db.get_user_transactions(session['user_id'], limit=5)
    notifications = db.get_unread_notifications(session['user_id'])
    total_balance = sum(a['balance'] for a in accounts)
    return render_template('customer/dashboard.html',
                           user=user, accounts=accounts,
                           recent_tx=recent_tx,
                           notifications=notifications,
                           total_balance=total_balance)


@app.route('/customer/accounts')
@login_required
@role_required('customer')
def customer_accounts():
    accounts = db.get_user_accounts(session['user_id'])
    return render_template('customer/accounts.html', accounts=accounts)


@app.route('/customer/transfer', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def customer_transfer():
    accounts        = db.get_user_accounts(session['user_id'])
    active_accounts = [a for a in accounts if a['status'] == 'active']

    if request.method == 'POST':
        from_id    = request.form.get('from_account')
        to_number  = request.form.get('to_account_number', '').strip()
        description= request.form.get('description', '').strip()
        try:
            amount = float(request.form.get('amount', 0))
            if amount <= 0:
                raise ValueError
        except ValueError:
            flash('Montant invalide.', 'danger')
            return render_template('customer/transfer.html', accounts=active_accounts)

        from_acc = db.get_account(from_id)
        if not from_acc or from_acc['user_id'] != session['user_id']:
            flash('Compte source invalide.', 'danger')
            return render_template('customer/transfer.html', accounts=active_accounts)
        if from_acc['status'] != 'active':
            flash('Ce compte est gelé ou fermé.', 'danger')
            return render_template('customer/transfer.html', accounts=active_accounts)
        if from_acc['balance'] < amount:
            flash('Solde insuffisant.', 'danger')
            return render_template('customer/transfer.html', accounts=active_accounts)

        to_acc = db.get_account_by_number(to_number)
        if not to_acc:
            flash('Compte destinataire introuvable.', 'danger')
            return render_template('customer/transfer.html', accounts=active_accounts)
        if to_acc['id'] == from_acc['id']:
            flash('Vous ne pouvez pas virer vers le même compte.', 'danger')
            return render_template('customer/transfer.html', accounts=active_accounts)

        db.create_transaction(from_acc['id'], to_acc['id'], amount, 'virement', description)
        db.add_notification(session['user_id'], 'Virement en attente',
                            f'Votre virement de {amount:,.2f} DNT est en cours de validation.')
        db.add_audit_log(session['user_id'], 'TRANSFER_REQUEST',
                         f'{amount} DNT → {to_number}', request.remote_addr)
        flash('Virement soumis. En attente d\'approbation.', 'success')
        return redirect(url_for('customer_history'))

    return render_template('customer/transfer.html', accounts=active_accounts)


@app.route('/customer/history')
@login_required
@role_required('customer')
def customer_history():
    page          = request.args.get('page', 1, type=int)
    filter_type   = request.args.get('type', '')
    filter_status = request.args.get('status', '')
    all_tx        = db.get_user_transactions(session['user_id'],
                                             tx_type=filter_type, status=filter_status)
    per_page      = 10
    total         = len(all_tx)
    start         = (page - 1) * per_page
    tx_page       = all_tx[start:start + per_page]
    total_pages   = max(1, (total + per_page - 1) // per_page)
    return render_template('customer/history.html',
                           transactions=tx_page, page=page,
                           total_pages=total_pages,
                           filter_type=filter_type,
                           filter_status=filter_status,
                           total=total)


@app.route('/customer/loans', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def customer_loans():
    if request.method == 'POST':
        try:
            amount   = float(request.form.get('amount', 0))
            duration = int(request.form.get('duration', 0))
            if amount <= 0 or duration <= 0:
                raise ValueError
        except ValueError:
            flash('Données invalides.', 'danger')
        else:
            purpose = request.form.get('purpose', '').strip()
            db.create_loan_request(session['user_id'], amount, duration, purpose)
            db.add_notification(session['user_id'], 'Demande de prêt soumise',
                                f'Demande de {amount:,.2f} DNT reçue.')
            flash('Demande de prêt soumise avec succès.', 'success')
        return redirect(url_for('customer_loans'))

    loans = db.get_user_loans(session['user_id'])
    return render_template('customer/loans.html', loans=loans)


@app.route('/customer/profile', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def customer_profile():
    user = db.get_user(session['user_id'])
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_info':
            full_name = request.form.get('full_name', '').strip()
            phone     = request.form.get('phone', '').strip()
            address   = request.form.get('address', '').strip()
            db.update_user_info(session['user_id'], full_name, phone, address)
            session['full_name'] = full_name
            flash('Informations mises à jour.', 'success')
        elif action == 'change_password':
            current = request.form.get('current_password', '')
            new_pw  = request.form.get('new_password', '')
            confirm = request.form.get('confirm_password', '')
            if not check_password_hash(user['password_hash'], current):
                flash('Mot de passe actuel incorrect.', 'danger')
            elif new_pw != confirm:
                flash('Les nouveaux mots de passe ne correspondent pas.', 'danger')
            elif len(new_pw) < 6:
                flash('6 caractères minimum requis.', 'danger')
            else:
                db.update_password(session['user_id'], generate_password_hash(new_pw))
                flash('Mot de passe changé avec succès.', 'success')
        return redirect(url_for('customer_profile'))
    return render_template('customer/profile.html', user=user)


@app.route('/customer/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    db.mark_all_notifications_read(session['user_id'])
    return jsonify({'status': 'ok'})


# ════════════════════════════════════════════════════════════════════════════
#  GESTIONNAIRE
# ════════════════════════════════════════════════════════════════════════════

@app.route('/gestionnaire/dashboard')
@login_required
@role_required('gestionnaire')
def gestionnaire_dashboard():
    stats = db.get_gestionnaire_stats()
    return render_template('gestionnaire/dashboard.html', stats=stats)


@app.route('/gestionnaire/pending')
@login_required
@role_required('gestionnaire')
def gestionnaire_pending():
    transactions = db.get_pending_transactions()
    return render_template('gestionnaire/pending.html', transactions=transactions)


@app.route('/gestionnaire/approve/<int:tx_id>', methods=['POST'])
@login_required
@role_required('gestionnaire')
def gestionnaire_approve(tx_id):
    tx = db.get_transaction(tx_id)
    if tx and tx['status'] == 'pending':
        from_acc = db.get_account(tx['from_account_id'])
        if from_acc and from_acc['balance'] >= tx['amount']:
            db.update_account_balance(tx['from_account_id'], -tx['amount'])
            db.update_account_balance(tx['to_account_id'],   tx['amount'])
            db.update_transaction_status(tx_id, 'completed', session['user_id'])
            from_user_id = from_acc['user_id']
            db.add_notification(from_user_id, 'Virement approuvé',
                                f'Votre virement de {tx["amount"]:,.2f} DNT a été exécuté.')
            db.add_audit_log(session['user_id'], 'APPROVE_TRANSFER',
                             f'Transaction #{tx_id}', request.remote_addr)
            flash('Virement approuvé et exécuté.', 'success')
        else:
            flash('Solde insuffisant dans le compte source.', 'danger')
    else:
        flash('Transaction introuvable ou déjà traitée.', 'danger')
    return redirect(url_for('gestionnaire_pending'))


@app.route('/gestionnaire/reject/<int:tx_id>', methods=['POST'])
@login_required
@role_required('gestionnaire')
def gestionnaire_reject(tx_id):
    tx = db.get_transaction(tx_id)
    if tx and tx['status'] == 'pending':
        comment      = request.form.get('comment', '')
        from_acc     = db.get_account(tx['from_account_id'])
        from_user_id = from_acc['user_id'] if from_acc else None
        db.update_transaction_status(tx_id, 'rejected', session['user_id'])
        if from_user_id:
            db.add_notification(from_user_id, 'Virement rejeté',
                                f'Virement de {tx["amount"]:,.2f} DNT rejeté. {comment}')
        db.add_audit_log(session['user_id'], 'REJECT_TRANSFER',
                         f'Transaction #{tx_id}: {comment}', request.remote_addr)
        flash('Virement rejeté.', 'warning')
    return redirect(url_for('gestionnaire_pending'))


@app.route('/gestionnaire/loans')
@login_required
@role_required('gestionnaire')
def gestionnaire_loans():
    loans = db.get_all_loans()
    return render_template('gestionnaire/loans.html', loans=loans)


@app.route('/gestionnaire/loans/approve/<int:loan_id>', methods=['POST'])
@login_required
@role_required('gestionnaire')
def gestionnaire_approve_loan(loan_id):
    loan = db.get_loan(loan_id)
    if loan and loan['status'] == 'pending':
        comment  = request.form.get('comment', '')
        accounts = db.get_user_accounts(loan['user_id'])
        if accounts:
            db.update_account_balance(accounts[0]['id'], loan['amount'])
        db.update_loan_status(loan_id, 'approved', session['user_id'], comment)
        db.add_notification(loan['user_id'], 'Prêt approuvé !',
                            f'Prêt de {loan["amount"]:,.2f} DNT approuvé et crédité.')
        db.add_audit_log(session['user_id'], 'APPROVE_LOAN',
                         f'Prêt #{loan_id}', request.remote_addr)
        flash('Prêt approuvé et montant crédité.', 'success')
    return redirect(url_for('gestionnaire_loans'))


@app.route('/gestionnaire/loans/reject/<int:loan_id>', methods=['POST'])
@login_required
@role_required('gestionnaire')
def gestionnaire_reject_loan(loan_id):
    loan = db.get_loan(loan_id)
    if loan and loan['status'] == 'pending':
        comment = request.form.get('comment', '')
        db.update_loan_status(loan_id, 'rejected', session['user_id'], comment)
        db.add_notification(loan['user_id'], 'Demande de prêt refusée',
                            f'Votre demande de {loan["amount"]:,.2f} DNT a été refusée. {comment}')
        db.add_audit_log(session['user_id'], 'REJECT_LOAN',
                         f'Prêt #{loan_id}: {comment}', request.remote_addr)
        flash('Demande refusée.', 'warning')
    return redirect(url_for('gestionnaire_loans'))


@app.route('/gestionnaire/accounts')
@login_required
@role_required('gestionnaire')
def gestionnaire_accounts():
    accounts = db.get_all_accounts_with_users()
    return render_template('gestionnaire/accounts.html', accounts=accounts)


@app.route('/gestionnaire/accounts/freeze/<int:acc_id>', methods=['POST'])
@login_required
@role_required('gestionnaire')
def gestionnaire_freeze_account(acc_id):
    acc = db.get_account(acc_id)
    if acc:
        new_status = 'frozen' if acc['status'] == 'active' else 'active'
        db.update_account_status(acc_id, new_status)
        action = 'FREEZE_ACCOUNT' if new_status == 'frozen' else 'UNFREEZE_ACCOUNT'
        db.add_audit_log(session['user_id'], action,
                         f'Compte #{acc_id}', request.remote_addr)
        flash('Gelé.' if new_status == 'frozen' else 'Dégelé.', 'success')
    return redirect(url_for('gestionnaire_accounts'))


# ════════════════════════════════════════════════════════════════════════════
#  ADMIN
# ════════════════════════════════════════════════════════════════════════════

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    stats        = db.get_admin_stats()
    monthly_data = db.get_monthly_stats()
    return render_template('admin/dashboard.html', stats=stats, monthly_data=monthly_data)


@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users/create', methods=['POST'])
@login_required
@role_required('admin')
def admin_create_user():
    full_name = request.form.get('full_name', '').strip()
    email     = request.form.get('email', '').strip()
    password  = request.form.get('password', '')
    role      = request.form.get('role', 'customer')
    phone     = request.form.get('phone', '').strip()

    if not all([full_name, email, password]):
        flash('Champs obligatoires manquants.', 'danger')
        return redirect(url_for('admin_users'))
    if db.get_user_by_email(email):
        flash('Email déjà utilisé.', 'danger')
        return redirect(url_for('admin_users'))

    uid = db.create_user(full_name, email, generate_password_hash(password), role, phone, '')
    if role == 'customer':
        db.create_account(uid, db.generate_account_number(), 'courant', 0.0)
    db.add_audit_log(session['user_id'], 'CREATE_USER',
                     f'Créé {email} [{role}]', request.remote_addr)
    flash(f'Utilisateur {full_name} créé.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_toggle_user(user_id):
    if user_id == session['user_id']:
        flash('Vous ne pouvez pas modifier votre propre statut.', 'danger')
        return redirect(url_for('admin_users'))
    user = db.get_user(user_id)
    if user:
        new_status = 0 if user['is_active'] else 1
        db.toggle_user_status(user_id, new_status)
        db.add_audit_log(session['user_id'],
                         'DEACTIVATE_USER' if new_status == 0 else 'ACTIVATE_USER',
                         f'User #{user_id}', request.remote_addr)
        flash('Statut mis à jour.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    if user_id == session['user_id']:
        flash('Vous ne pouvez pas supprimer votre propre compte.', 'danger')
        return redirect(url_for('admin_users'))
    db.delete_user(user_id)
    db.add_audit_log(session['user_id'], 'DELETE_USER',
                     f'User #{user_id}', request.remote_addr)
    flash('Utilisateur supprimé.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/accounts')
@login_required
@role_required('admin')
def admin_accounts():
    accounts = db.get_all_accounts_with_users()
    return render_template('admin/accounts.html', accounts=accounts)


@app.route('/admin/accounts/freeze/<int:acc_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_freeze_account(acc_id):
    acc = db.get_account(acc_id)
    if acc:
        new_status = 'frozen' if acc['status'] == 'active' else 'active'
        db.update_account_status(acc_id, new_status)
        db.add_audit_log(session['user_id'], 'TOGGLE_ACCOUNT',
                         f'Compte #{acc_id} → {new_status}', request.remote_addr)
        flash(f'Compte {"gelé" if new_status == "frozen" else "activé"}.', 'success')
    return redirect(url_for('admin_accounts'))


@app.route('/admin/accounts/credit/<int:acc_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_credit_account(acc_id):
    try:
        amount = float(request.form.get('amount', 0))
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash('Montant invalide.', 'danger')
        return redirect(url_for('admin_accounts'))
    db.update_account_balance(acc_id, amount)
    db.create_transaction(None, acc_id, amount, 'depot', 'Dépôt administratif', 'completed')
    db.add_audit_log(session['user_id'], 'CREDIT_ACCOUNT',
                     f'Compte #{acc_id} +{amount} DNT', request.remote_addr)
    flash(f'{amount:,.2f} DNT crédités.', 'success')
    return redirect(url_for('admin_accounts'))


@app.route('/admin/transactions')
@login_required
@role_required('admin')
def admin_transactions():
    filter_status = request.args.get('status', '')
    transactions  = db.get_all_transactions(status=filter_status)
    return render_template('admin/transactions.html',
                           transactions=transactions, filter_status=filter_status)


@app.route('/admin/logs')
@login_required
@role_required('admin')
def admin_logs():
    logs = db.get_audit_logs()
    return render_template('admin/logs.html', logs=logs)


# ════════════════════════════════════════════════════════════════════════════
#  API (JSON)
# ════════════════════════════════════════════════════════════════════════════

@app.route('/api/account-lookup/<account_number>')
@login_required
def api_account_lookup(account_number):
    acc = db.get_account_by_number(account_number)
    if acc and acc['status'] == 'active':
        user = db.get_user(acc['user_id'])
        return jsonify({'found': True,
                        'owner': user['full_name'],
                        'type': acc['account_type']})
    return jsonify({'found': False})


@app.route('/api/monthly-stats')
@login_required
@role_required('admin')
def api_monthly_stats():
    return jsonify(db.get_monthly_stats())


# ════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT & INITIALIZATION
# ════════════════════════════════════════════════════════════════════════════

with app.app_context():
    try:
        conn = db.get_db()
        # Check if table exists (avoids re-initializing if already done)
        exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        conn.close()
        if not exists:
            db.init_db()
            db.seed_demo_data()
            print("Database initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")

if __name__ == '__main__':
    app.run(debug=True, port=5050, host='0.0.0.0')
