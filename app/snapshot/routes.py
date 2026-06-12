from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.snapshot import snapshot_bp
from app.models import MasterItem, StockOpnameSession, StockSnapshot, ActivityLog, Category
from app import db
from datetime import datetime, timedelta

INDONESIAN_MONTHS = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

def log_activity(action, entity_type, entity_id, description):
    log = ActivityLog(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description
    )
    db.session.add(log)

@snapshot_bp.route('/opname', methods=['GET', 'POST'])
@login_required
def opname():
    if request.method == 'POST':
        items = MasterItem.query.filter_by(deleted_at=None).all()
        has_updates = False
        
        # 1. Amankan ID Unik Sesi Terlebih Dahulu (Mencegah Race Condition)
        new_session = StockOpnameSession(
            session_code="TEMP-HOLD", 
            created_by=current_user.id,
            notes=request.form.get('session_notes', 'Opname Berkala').strip()
        )
        db.session.add(new_session)
        db.session.flush() 
        
        # 2. Konstruksi Kode Sesi Menggunakan Kombinasi Tanggal dan ID Database Absolut
        date_str = datetime.now().strftime('%Y%m%d')
        new_session.session_code = f"SO-{date_str}-{new_session.id:04d}"
        
        for item in items:
            input_val = request.form.get(f'stock_{item.id}')
            if input_val and input_val.strip() != '':
                try:
                    physical_qty = int(input_val)
                    system_qty_before = item.current_stock
                    variance = physical_qty - system_qty_before
                    
                    new_snapshot = StockSnapshot(
                        session_id=new_session.id,
                        item_id=item.id,
                        physical_qty=physical_qty,
                        system_qty_before=system_qty_before,
                        variance_qty=variance,
                        created_by=current_user.id
                    )
                    db.session.add(new_snapshot)
                    item.current_stock = physical_qty
                    has_updates = True
                except ValueError:
                    continue
        
        if has_updates:
            log_activity('OPNAME', 'STOCK_SESSION', new_session.id, f"Melakukan stock opname: {new_session.session_code}")
            db.session.commit()
            flash(f'Proses Stock Opname ({new_session.session_code}) berhasil disimpan!', 'success')
        else:
            db.session.rollback()
            flash('Tidak ada perubahan stok yang dicatat.', 'info')
            
        return redirect(url_for('snapshot.history'))

   
    category_filter = request.args.get('category_id')
    query = MasterItem.query.filter_by(deleted_at=None)
    
    if category_filter:
        query = query.filter_by(category_id=category_filter)
        
    items = query.all()
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('snapshot/opname.html', items=items, categories=categories, current_cat=category_filter)
@snapshot_bp.route('/history')
@login_required
def history():
    filter_type = request.args.get('filter_type', 'today')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = StockOpnameSession.query
    now = datetime.now()

    # Logika Cerdas Pemilihan Rentang Waktu Otomatis (Default Hari Ini)
    if filter_type == 'today':
        start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now.replace(hour=23, minute=59, second=59, microsecond=999)
        query = query.filter(StockOpnameSession.session_datetime.between(start_dt, end_dt))
    elif filter_type == 'week':
        start_dt = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0)
        query = query.filter(StockOpnameSession.session_datetime >= start_dt)
    elif filter_type == 'month':
        start_dt = now.replace(day=1, hour=0, minute=0, second=0)
        query = query.filter(StockOpnameSession.session_datetime >= start_dt)
    elif filter_type == 'custom' and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(StockOpnameSession.session_datetime.between(start_dt, end_dt))
        except ValueError:
            pass

    sessions = query.order_by(StockOpnameSession.session_datetime.desc()).all()

    # Struktur Pengelompokan Data Bersusun Vertikal (Tahun -> Bulan -> Sesi)
    grouped_history = {}
    for sess in sessions:
        year = sess.session_datetime.strftime('%Y')
        month_name = INDONESIAN_MONTHS[sess.session_datetime.month]
        
        if year not in grouped_history:
            grouped_history[year] = {}
        if month_name not in grouped_history[year]:
            grouped_history[year][month_name] = []
            
        grouped_history[year][month_name].append(sess)

    return render_template(
        'snapshot/history.html', 
        grouped_history=grouped_history, 
        filter_type=filter_type,
        start_date=start_date,
        end_date=end_date
    )