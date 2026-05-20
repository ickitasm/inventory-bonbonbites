from flask import Blueprint

# 1. Inisialisasi Blueprint
snapshot_bp = Blueprint('snapshot', __name__)

# 2. Import routes di bagian PALING BAWAH
from app.snapshot import routes