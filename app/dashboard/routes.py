from flask import render_template
from flask_login import login_required, current_user
from app.dashboard import dashboard_bp
from app.models import MasterItem, StockSnapshot

@dashboard_bp.route('/')
@login_required
def index():
    # 1. Total Item Aktif (Belum Dihapus)
    total_items = MasterItem.query.filter_by(deleted_at=None).count()
    
    # 2. Total Item Stok Rendah (Current Stock <= ROP)
    low_stock_items = MasterItem.query.filter(
        MasterItem.current_stock <= MasterItem.reorder_point, 
        MasterItem.deleted_at == None
    ).count()
    
    # 3. Total Aktivitas Opname yang sudah terekam
    total_opname = StockSnapshot.query.count()
    
    # 4. Ambil 5 Item dengan stok paling kritis untuk ditampilkan di tabel
    critical_items = MasterItem.query.filter(
        MasterItem.current_stock <= MasterItem.reorder_point,
        MasterItem.deleted_at == None
    ).order_by(MasterItem.current_stock.asc()).limit(5).all()

    return render_template(
        'dashboard/index.html', 
        user=current_user,
        total_items=total_items,
        low_stock_items=low_stock_items,
        total_opname=total_opname,
        critical_items=critical_items
    )