from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.snapshot import snapshot_bp
from app.models import MasterItem, StockSnapshot
from app import db
from datetime import datetime

@snapshot_bp.route('/opname', methods=['GET', 'POST'])
@login_required
def opname():
    if request.method == 'POST':
        items = MasterItem.query.filter_by(deleted_at=None).all()
        has_updates = False
        
        for item in items:
            input_val = request.form.get(f'stock_{item.id}')
            if input_val and input_val.strip() != '':
                try:
                    actual_qty = int(input_val)
                    if actual_qty != item.current_stock:
                        new_snapshot = StockSnapshot(
                            item_id=item.id,
                            actual_qty=actual_qty,
                            created_by=current_user.id
                        )
                        db.session.add(new_snapshot)
                        item.current_stock = actual_qty
                        has_updates = True
                except ValueError:
                    continue
        
        if has_updates:
            db.session.commit()
            flash('Proses Stock Opname berhasil disimpan ke database!', 'success')
        else:
            flash('Tidak ada perubahan stok yang dicatat.', 'info')
            
        return redirect(url_for('snapshot.history'))

    items = MasterItem.query.filter_by(deleted_at=None).all()
    return render_template('snapshot/opname.html', items=items)

@snapshot_bp.route('/history')
@login_required
def history():
    # Menangkap filter dari URL (GET Request)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = StockSnapshot.query

    # Jika ada input tanggal mulai
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(StockSnapshot.snapshot_at >= start_dt)
        except ValueError:
            pass

    # Jika ada input tanggal akhir (dibuat hingga pukul 23:59:59)
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(StockSnapshot.snapshot_at <= end_dt)
        except ValueError:
            pass

    snapshots = query.order_by(StockSnapshot.snapshot_at.desc()).all()
    return render_template('snapshot/history.html', snapshots=snapshots, start_date=start_date, end_date=end_date)