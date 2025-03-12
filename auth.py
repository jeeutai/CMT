import csv
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import login_manager
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

class User(UserMixin):
    def __init__(self, id, username, password_hash, is_admin=False, balance=1000):
        self.id = int(id)
        self.username = username
        self.password_hash = password_hash
        self.is_admin = isinstance(is_admin, bool) and is_admin or str(is_admin).lower() == 'true'
        self.balance = float(balance)

def init_users_csv():
    """Initialize users.csv with admin account"""
    os.makedirs('data', exist_ok=True)
    admin_password = 'admin'
    admin_hash = generate_password_hash(admin_password)
    logger.debug(f"Creating new admin account with hash: {admin_hash}")

    with open('data/users.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'username', 'password_hash', 'is_admin', 'balance'])
        writer.writerow([1, 'admin', admin_hash, 'true', 10000])

def load_users():
    users = {}
    if not os.path.exists('data/users.csv'):
        init_users_csv()

    try:
        with open('data/users.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                logger.debug(f"Loading user data: {row}")
                users[row['username']] = User(
                    id=row['id'],
                    username=row['username'],
                    password_hash=row['password_hash'],
                    is_admin=row['is_admin'],
                    balance=row['balance']
                )
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        raise

    logger.debug(f"Loaded users: {[user.username for user in users.values()]}")
    return users

def get_next_user_id():
    users = load_users()
    return max((user.id for user in users.values()), default=0) + 1

@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    for user in users.values():
        if user.id == int(user_id):
            return user
    return None

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()

        logger.debug(f"Login attempt for username: {username}")

        if username in users:
            user = users[username]
            logger.debug(f"Found user {username}, checking password")
            if check_password_hash(user.password_hash, password):
                login_user(user)
                logger.info(f"User {username} logged in successfully")
                flash('로그인되었습니다.')
                return redirect(url_for('transaction.dashboard'))
            else:
                logger.warning(f"Invalid password for username: {username}")

        flash('잘못된 사용자 이름 또는 비밀번호입니다.')
        logger.warning(f"Failed login attempt for username: {username}")

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        users = load_users()
        if username in users:
            flash('이미 존재하는 사용자 이름입니다.')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('비밀번호가 일치하지 않습니다.')
            return redirect(url_for('auth.register'))

        new_user_id = get_next_user_id()
        with open('data/users.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                new_user_id,
                username,
                generate_password_hash(password),
                'false',  # is_admin
                1000    # initial balance
            ])

        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.')
    return redirect(url_for('auth.login'))