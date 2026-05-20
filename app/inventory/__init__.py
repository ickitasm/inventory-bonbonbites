from flask import Blueprint

# Inisialisasi blueprint
inventory_bp = Blueprint('inventory', __name__)

# Import routes di bawah inisialisasi untuk menghindari circular import
from app.inventory import routes