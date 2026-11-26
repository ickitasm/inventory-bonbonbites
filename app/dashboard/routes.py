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

    # 3. Hitung kapasitas riil database PostgreSQL (Supabase Free Tier = 500 MB)
    db_used_mb = 0.0
    db_limit_mb = 500.0
    db_percent = 0.0
    db_supported = False

    try:
        size_bytes = db.session.execute(
            text("SELECT pg_database_size(current_database())")
        ).scalar()
        if size_bytes is not None:
            db_used_mb = round(size_bytes / (1024 * 1024), 2)
            db_percent = round((db_used_mb / db_limit_mb) * 100, 2)
            db_supported = True
    except Exception:
        db.session.rollback()

    return render_template(
        'dashboard/index.html',
        total_items=total_items,
        low_stock_count=low_stock_count,
        total_sessions=total_sessions,
        critical_items=critical_items,
        db_used_mb=db_used_mb,
        db_limit_mb=int(db_limit_mb),
        db_percent=db_percent,
        db_supported=db_supported
    )