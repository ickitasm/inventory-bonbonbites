from flask import Blueprint

# Inisialisasi blueprint
auth_bp = Blueprint('auth', __name__)

# Import routes di bawah inisialisasi untuk menghindari circular import
from app.auth import routes