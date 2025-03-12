import os
from flask import Flask
from flask_login import LoginManager
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "chess-empire-secret-key")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import routes after app initialization to avoid circular imports
from auth import auth_bp
from transaction import transaction_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(transaction_bp)
