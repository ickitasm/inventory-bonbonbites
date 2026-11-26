import io
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.snapshot import snapshot_bp
from app.models import (
    User, MasterItem, StockOpnameSession, StockSnapshot,
    ActivityLog, Category, StorageLocation
)
from app import db
from app.utils import roles_required

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
@roles_required('admin', 'manager', 'staff')
def opname():
    if request.method == 'POST':
        items = MasterItem.query.filter_by(deleted_at=None).all()
        has_updates = False
        
        new_session = StockOpnameSession(
            session_code="TEMP-HOLD", 
            created_by=current_user.id,
            notes=request.form.get('session_notes', 'Opname Berkala').strip()
        )
        db.session.add(new_session)
        db.session.flush() 
        
        date_str = datetime.now().strftime('%Y%m%d')
        new_session.session_code = f"SO-{date_str}-{new_session.id:04d}"
        
        for item in items:
            input_val = request.form.get(f'stock_{item.id}')
            if input_val and input_val.strip() != '':
                try:
                    normalized_val = input_val.strip().replace(',', '.')
                    physical_qty = round(Decimal(normalized_val), 2)
                    if physical_qty < 0:
                        continue

                    system_qty_before = Decimal(str(item.current_stock or 0))
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
                except (InvalidOperation, ValueError):
                    continue
        
        if has_updates:
            log_activity('OPNAME', 'STOCK_SESSION', new_session.id, f"Melakukan stock opname: {new_session.session_code}")
            db.session.commit()
            flash(f'Proses Stock Opname ({new_session.session_code}) berhasil disimpan!', 'success')
        else:
            db.session.rollback()
            flash('Tidak ada perubahan stok yang dicatat.', 'info')
            
        return redirect(url_for('snapshot.history'))

    category_filter = request.args.get('category_id', '')
    location_filter = request.args.get('location_id', '')
    
    items = MasterItem.query.filter_by(deleted_at=None).order_by(MasterItem.item_name.asc()).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.category_name.asc()).all()
    locations = StorageLocation.query.filter_by(is_active=True).order_by(
        StorageLocation.floor_code.asc(),
        StorageLocation.location_code.asc()
    ).all()
    location_map = {loc.id: loc for loc in locations}
    
    return render_template(
        'snapshot/opname.html',
        items=items,
        categories=categories,
        locations=locations,
        location_map=location_map,
        current_cat=category_filter,
        current_loc=location_filter
    )

@snapshot_bp.route('/history')
@login_required
@roles_required('Admin', 'Manager', 'Staff')
def history():
    filter_type = request.args.get('filter_type', 'today')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = StockOpnameSession.query
    now = datetime.now()

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

@snapshot_bp.route('/history/export/<int:session_id>')
@login_required
@roles_required('Admin', 'Manager', 'Staff')
def export_session_excel(session_id):
    session = StockOpnameSession.query.get_or_404(session_id)
    snapshots = StockSnapshot.query.filter_by(session_id=session.id).all()

    # Lookup map agar query tetap ringan (menghindari N+1 query)
    items_map = {i.id: i for i in MasterItem.query.all()}
    categories_map = {c.id: c.category_name for c in Category.query.all()}
    locations_map = {
        l.id: f"{l.floor_code} - {l.storage_type} ({l.location_code})"
        for l in StorageLocation.query.all()
    }
    creator = db.session.get(User, session.created_by)
    creator_name = creator.full_name if creator and creator.full_name else (creator.username if creator else '-')

    wb = Workbook()
    ws = wb.active
    ws.title = "Hasil Stock Opname"

    # Styling standar laporan
    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    meta_label_font = Font(name="Calibri", size=10, bold=True, color="475569")
    meta_val_font = Font(name="Calibri", size=10, color="0F172A")
    header_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="312E81", end_color="312E81", fill_type="solid")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    thin_side = Side(style="thin", color="CBD5E1")
    cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # Blok Identitas Sesi
    ws["A1"] = "LAPORAN HASIL STOCK OPNAME - BONBONBITES"
    ws["A1"].font = title_font

    meta_rows = [
        ("Kode Sesi", session.session_code),
        ("Waktu Pelaksanaan", session.session_datetime.strftime('%d-%m-%Y %H:%M')),
        ("Petugas Opname", creator_name),
        ("Catatan Sesi", session.notes or "-"),
    ]
    for idx, (label, val) in enumerate(meta_rows, start=3):
        ws.cell(row=idx, column=1, value=label).font = meta_label_font
        ws.cell(row=idx, column=2, value=val).font = meta_val_font

    # Header Tabel Data (Baris ke-8)
    start_row = 8
    headers = [
        "No", "Kode SKU", "Nama Barang", "Kategori", "Lokasi Penyimpanan",
        "Satuan", "Stok Sistem", "Stok Fisik", "Selisih", "Status"
    ]
    for col_idx, text in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=text)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = cell_border

    # Urutkan data berdasarkan lokasi lalu nama barang seperti alur lapangan
    def sort_key(snap):
        item = items_map.get(snap.item_id)
        loc_str = locations_map.get(item.storage_location_id, "ZZZ") if item else "ZZZ"
        name_str = item.item_name if item else ""
        return (loc_str, name_str)

    sorted_snapshots = sorted(snapshots, key=sort_key)

    for idx, snap in enumerate(sorted_snapshots, start=1):
        row_num = start_row + idx
        item = items_map.get(snap.item_id)

        sku = item.item_code if item else "-"
        name = item.item_name if item else f"Item #{snap.item_id}"
        cat_name = categories_map.get(item.category_id, "-") if item else "-"
        loc_name = locations_map.get(item.storage_location_id, "-") if item else "-"
        unit = item.unit if item else "-"

        sys_qty = float(snap.system_qty_before or 0)
        phy_qty = float(snap.physical_qty or 0)
        var_qty = float(snap.variance_qty or 0)

        if var_qty > 0:
            status_text = "Lebih (+)"
            var_color = "15803D"
        elif var_qty < 0:
            status_text = "Kurang (-)"
            var_color = "B91C1C"
        else:
            status_text = "Sesuai"
            var_color = "475569"

        row_values = [
            idx, sku, name, cat_name, loc_name,
            unit, sys_qty, phy_qty, var_qty, status_text
        ]

        for col_idx, val in enumerate(row_values, start=1):
            cell = ws.cell(row=row_num, column=col_idx, value=val)
            cell.border = cell_border
            if idx % 2 == 0:
                cell.fill = zebra_fill

            if col_idx in (1, 2, 6, 10):
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx in (7, 8, 9):
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "#,##0.##"
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

            if col_idx in (9, 10):
                cell.font = Font(name="Calibri", size=10, bold=True, color=var_color)

    # Lebar kolom otomatis agar teks tidak terpotong
    column_widths = {
        "A": 6, "B": 16, "C": 32, "D": 20, "E": 30,
        "F": 10, "G": 14, "H": 14, "I": 14, "J": 14
    }
    for col_letter, width in column_widths.items():
        ws.column_dimensions[col_letter].width = width

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    log_activity('EXPORT', 'STOCK_SESSION', session.id, f"Mengekspor Excel sesi opname: {session.session_code}")
    db.session.commit()

    filename = f"{session.session_code}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )