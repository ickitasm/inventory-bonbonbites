from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user # Pastikan current_user diimpor
from app.snapshot import snapshot_bp
from app.models import MasterItem, StockSnapshot
from app import db
from datetime import datetime

@snapshot_bp.route('/opname', methods=['GET', 'POST'])
@login_required
def opname():
    if request.method == 'POST':
        # Proses menyimpan data dari form
        for key, value in request.form.items():
            if key.startswith('stock_'):
                item_id = key.split('_')[1]
                actual_qty = int(value)
                
                # Perbaikan 1: Gunakan 'snapshot_at' bukan 'snapshot_date'
                # Perbaikan 2: Wajib mengisi 'created_by' dari current_user.id
                new_snapshot = StockSnapshot(
                    item_id=item_id, 
                    actual_qty=actual_qty, 
                    snapshot_at=datetime.utcnow(), 
                    created_by=current_user.id
                )
                db.session.add(new_snapshot)
                
                # Update juga current_stock di MasterItem
                item = MasterItem.query.get(item_id)
                if item:
                    item.current_stock = actual_qty
        
        db.session.commit()
        flash('Data opname berhasil disimpan!', 'success')
        return redirect(url_for('snapshot.opname'))

    # Perbaikan 3: Filter item yang deleted_at nya NULL (belum dihapus)
    items = MasterItem.query.filter(MasterItem.deleted_at == None).all()
    
    return render_template('snapshot/opname.html', items=items)


@snapshot_bp.route('/history')
@login_required
def history():
    # Mengambil semua data opname, diurutkan dari yang terbaru ke terlama
    # Karena di models.py Anda sudah membuat backref='item' dan backref='author',
    # kita bisa langsung memanggil relasinya di HTML nanti.
    snapshots = StockSnapshot.query.order_by(StockSnapshot.snapshot_at.desc()).all()
    
    return render_template('snapshot/history.html', snapshots=snapshots)