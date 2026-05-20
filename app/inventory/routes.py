from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.inventory import inventory_bp
from app.models import MasterItem
from datetime import datetime

# Daftar opsi standar untuk Data Governance
CATEGORIES = ['PREMIX', 'BARANG_FRESH', 'FREEZER_LNT3', 'CHILLER_LNT3', 'RAK_LNT3', 'PACKAGING', 'MINUMAN', 'LNT1']
UNITS = ['GRAM', 'KG', 'PCS', 'PACK', 'KARTON', 'LITER', 'ML']

@inventory_bp.route('/items')
@login_required
def list_items():
    # Hanya ambil barang yang belum di-soft delete
    items = MasterItem.query.filter_by(deleted_at=None).all()
    # UBAH BARIS DI BAWAH INI:
    return render_template('inventory/items.html', items=items, categories=CATEGORIES, units=UNITS)

@inventory_bp.route('/items/create', methods=['POST'])
@login_required
def create_item():
    name = request.form.get('name').strip()
    category = request.form.get('category')
    unit = request.form.get('unit')
    reorder_point = request.form.get('reorder_point', 0)

    # Validasi Unique Name (Aktif)
    existing_item = MasterItem.query.filter_by(name=name, deleted_at=None).first()
    if existing_item:
        flash(f"Barang dengan nama '{name}' sudah ada!", "danger")
        return redirect(url_for('inventory.list_items'))

    # Auto-generate SKU Sederhana berdasarkan jumlah item saat ini + 1
    # Contoh: RAW-0001, PKG-0002
    prefix = "RAW" if category != "PACKAGING" else "PKG"
    item_count = MasterItem.query.count() + 1
    item_code = f"{prefix}-{item_count:04d}"

    new_item = MasterItem(
        item_code=item_code,
        name=name,
        category=category,
        unit=unit,
        reorder_point=int(reorder_point) if reorder_point else 0,
        current_stock=0 # WAJIB 0, hanya bisa berubah lewat opname/snapshot
    )
    
    db.session.add(new_item)
    db.session.commit()
    flash(f"Barang {name} ({item_code}) berhasil didaftarkan!", "success")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/items/update/<int:id>', methods=['POST'])
@login_required
def update_item(id):
    item = MasterItem.query.get_or_404(id)
    name = request.form.get('name').strip()
    
    # Cek duplikasi nama dengan barang lain
    existing_item = MasterItem.query.filter(MasterItem.id != id, MasterItem.name == name, MasterItem.deleted_at == None).first()
    if existing_item:
        flash(f"Nama '{name}' sudah digunakan oleh barang lain!", "danger")
        return redirect(url_for('inventory.list_items'))

    item.name = name
    item.category = request.form.get('category')
    item.unit = request.form.get('unit')
    item.reorder_point = int(request.form.get('reorder_point', 0))
    # PERHATIKAN: item.current_stock TIDAK DISENTUH SAMA SEKALI DISINI (READ-ONLY)

    db.session.commit()
    flash(f"Data barang {item.item_code} berhasil diperbarui!", "success")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/items/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    item = MasterItem.query.get_or_404(id)
    item.deleted_at = datetime.utcnow() # Soft delete
    db.session.commit()
    flash(f"Barang {item.name} berhasil dihapus dari sistem!", "warning")
    return redirect(url_for('inventory.list_items'))