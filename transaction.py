import csv
import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
import logging

transaction_bp = Blueprint('transaction', __name__)
logger = logging.getLogger(__name__)

def update_balance(username, amount):
    users = []
    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['username'] == username:
                new_balance = float(row['balance']) + amount
                if new_balance < 0:
                    return False
                row['balance'] = str(new_balance)
            users.append(row)

    with open('data/users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'username', 'password_hash', 'is_admin', 'balance'])
        writer.writeheader()
        writer.writerows(users)
    return True

def record_transaction(sender, receiver, amount, transaction_type="transfer"):
    os.makedirs('data', exist_ok=True)
    if not os.path.exists('data/transactions.csv'):
        with open('data/transactions.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'sender', 'receiver', 'amount', 'type'])

    with open('data/transactions.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), sender, receiver, amount, transaction_type])

def get_total_balance():
    total = 0
    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += float(row['balance'])
    return total

@transaction_bp.route('/')
@transaction_bp.route('/dashboard')
@login_required
def dashboard():
    transactions = []
    if os.path.exists('data/transactions.csv'):
        with open('data/transactions.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['sender'] == current_user.username or row['receiver'] == current_user.username:
                    transactions.append(row)

    return render_template('dashboard.html', transactions=transactions)

@transaction_bp.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if request.method == 'POST':
        receiver = request.form['receiver']
        amount = float(request.form['amount'])

        if amount <= 0:
            flash('금액은 0보다 커야 합니다.')
            return redirect(url_for('transaction.transfer'))

        if amount > current_user.balance:
            flash('잔액이 부족합니다.')
            return redirect(url_for('transaction.transfer'))

        # Update balances
        if update_balance(current_user.username, -amount):
            if update_balance(receiver, amount):
                # Record transaction
                record_transaction(current_user.username, receiver, amount)
                flash('송금이 완료되었습니다.')
            else:
                update_balance(current_user.username, amount)  # Rollback
                flash('수취인을 찾을 수 없습니다.')
        else:
            flash('송금에 실패했습니다.')
        return redirect(url_for('transaction.dashboard'))

    return render_template('transfer.html')

@transaction_bp.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    transactions = []
    users = []

    with open('data/transactions.csv', 'r') as f:
        reader = csv.DictReader(f)
        transactions = list(reader)

    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        users = list(reader)

    total_balance = get_total_balance()

    return render_template('admin.html', transactions=transactions, users=users, total_balance=total_balance)

@transaction_bp.route('/admin/add_user', methods=['POST'])
@login_required
def add_user():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    username = request.form['username']
    password = request.form['password']
    initial_balance = float(request.form['initial_balance'])
    is_admin = 'is_admin' in request.form

    # Check if username already exists
    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        if any(row['username'] == username for row in reader):
            flash('이미 존재하는 사용자 이름입니다.')
            return redirect(url_for('transaction.admin'))

    # Add new user
    with open('data/users.csv', 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            len(list(csv.reader(open('data/users.csv')))) + 1,
            username,
            generate_password_hash(password),
            str(is_admin).lower(),
            initial_balance
        ])

    flash('사용자가 추가되었습니다.')
    return redirect(url_for('transaction.admin'))

@transaction_bp.route('/admin/edit_user', methods=['POST'])
@login_required
def edit_user():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    original_username = request.form['original_username']
    new_username = request.form['new_username']
    new_password = request.form['new_password']

    users = []
    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['username'] == original_username:
                if new_username:
                    row['username'] = new_username
                if new_password:
                    row['password_hash'] = generate_password_hash(new_password)
            users.append(row)

    with open('data/users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'username', 'password_hash', 'is_admin', 'balance'])
        writer.writeheader()
        writer.writerows(users)

    flash('사용자 정보가 수정되었습니다.')
    return redirect(url_for('transaction.admin'))

@transaction_bp.route('/admin/delete_user', methods=['POST'])
@login_required
def delete_user():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    username = request.form['username']
    if username == 'admin':
        flash('관리자 계정은 삭제할 수 없습니다.')
        return redirect(url_for('transaction.admin'))

    users = []
    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        users = [row for row in reader if row['username'] != username]

    with open('data/users.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'username', 'password_hash', 'is_admin', 'balance'])
        writer.writeheader()
        writer.writerows(users)

    flash('사용자가 삭제되었습니다.')
    return redirect(url_for('transaction.admin'))

@transaction_bp.route('/admin/fine_user', methods=['POST'])
@login_required
def fine_user():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    username = request.form['username']
    amount = float(request.form['amount'])
    reason = request.form['reason']

    if update_balance(username, -amount):
        record_transaction(username, 'SYSTEM', amount, 'fine')
        flash(f'벌금이 부과되었습니다. 사유: {reason}')
    else:
        flash('벌금 부과에 실패했습니다. 잔액이 부족합니다.')

    return redirect(url_for('transaction.admin'))

@transaction_bp.route('/admin/pay_salary', methods=['POST'])
@login_required
def pay_salary():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    amount = float(request.form['amount'])

    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        users = list(reader)

    for user in users:
        if user['username'] != 'admin':
            update_balance(user['username'], amount)
            record_transaction('SYSTEM', user['username'], amount, 'salary')

    flash(f'모든 사용자에게 {amount} 체스머니의 주급이 지급되었습니다.')
    return redirect(url_for('transaction.admin'))

@transaction_bp.route('/admin/collect_tax', methods=['POST'])
@login_required
def collect_tax():
    if not current_user.is_admin:
        flash('관리자 권한이 필요합니다.')
        return redirect(url_for('transaction.dashboard'))

    tax_rate = float(request.form['percentage']) / 100

    with open('data/users.csv', 'r') as f:
        reader = csv.DictReader(f)
        users = list(reader)

    for user in users:
        if user['username'] != 'admin':
            tax_amount = float(user['balance']) * tax_rate
            if update_balance(user['username'], -tax_amount):
                record_transaction(user['username'], 'SYSTEM', tax_amount, 'tax')

    flash(f'모든 사용자에게 {tax_rate*100}%의 세금이 징수되었습니다.')
    return redirect(url_for('transaction.admin'))