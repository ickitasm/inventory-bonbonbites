from flask import render_template
from sqlalchemy import text
from app import db
from app.dashboard import dashboard_bp
from app.models import MasterItem, StockOpnameSession
from app.utils import roles_required


@dashboard_bp.route('/')
@dashboard_bp.route('/index')
@roles_required('Admin', 'Manager', 'Staff')
def index():
    # 1. Hitung statistik agregat berdasarkan struktur DB baru
    total_items = MasterItem.query.filter_by(deleted_at=None).count()

    low_stock_count = MasterItem.query.filter(
        MasterItem.deleted_at == None,
        MasterItem.current_stock <= MasterItem.reorder_point
    ).count()

    total_sessions = StockOpnameSession.query.count()

    # 2. Ambil Top 5 Barang Paling Kritis untuk Early Warning System
    critical_items = MasterItem.query.filter(
        MasterItem.deleted_at == None,
        MasterItem.current_stock <= MasterItem.reorder_point
    ).order_by(MasterItem.current_stock.asc()).limit(5).all()

    