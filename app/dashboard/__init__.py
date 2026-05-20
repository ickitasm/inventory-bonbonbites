from flask import Blueprint

# Inisialisasi blueprint
dashboard_bp = Blueprint('dashboard', __name__)

# Import routes di bawah inisialisasi untuk menghindari circular import
from app.dashboard import routes