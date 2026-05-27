from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.inventory import inventory_bp
from app.models import MasterItem, Category, StorageLocation, Supplier
from datetime import datetime

# Opsi Satuan Standar tetap dipertahankan berupa list teks biasa
UNITS = ['GRAM', 'KG', 'PCS', 'PACK', 'KARTON', 'LITER', 'ML']

@inventory_bp.route('/items')
@login_required
def list_items():
    # Hanya ambil barang yang belum di-soft delete
    items = MasterItem.query.filter_by(deleted_at=None).all()
    
    # Ambil data master pendukung untuk disuntikkan ke dropdown Form modal HTML
    categories = Category.query.all()
    locations = StorageLocation.query.all()
    suppliers = Supplier.query.all()
    
    return render_template(
        'inventory/items.html', 
        items=items, 
        categories=categories, 
        locations=locations, 
        suppliers=suppliers,
        units=UNITS
    )

@inventory_bp.route('/items/create', methods=['POST'])
@login_required
def create_item():
    name = request.form.get('name').strip()
    category_id = request.form.get('category_id')
    location_id = request.form.get('location_id')
    supplier_id = request.form.get('supplier_id')
    unit = request.form.get('unit')
    reorder_point = request.form.get('reorder_point', 0)
    notes = request.form.get('notes', '').strip()

    # Validasi Unique Name
    existing_item = MasterItem.query.filter_by(name=name, deleted_at=None).first()
    if existing_item:
        flash(f"Barang dengan nama '{name}' sudah ada!", "danger")
        return redirect(url_for('inventory.list_items'))

    # Auto-generate SKU berdasarkan nama kategori objek
    cat_obj = Category.query.get(category_id)
    prefix = "PKG" if cat_obj and cat_obj.name == "PACKAGING" else "RAW"
    
    item_count = MasterItem.query.count() + 1
    item_code = f"{prefix}-{item_count:04d}"

    new_item = MasterItem(
        item_code=item_code,
        name=name,
        category_id=int(category_id) if category_id else None,
        location_id=int(location_id) if location_id else None,
        supplier_id=int(supplier_id) if supplier_id else None,
        unit=unit,
        reorder_point=int(reorder_point) if reorder_point else 0,
        current_stock=0, # Aturan baku: Wajib 0 di awal, berubah hanya lewat opname
        notes=notes
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
    
    existing_item = MasterItem.query.filter(
        MasterItem.id != id, 
        MasterItem.name == name, 
        MasterItem.deleted_at == None
    ).first()
    
    if existing_item:
        flash(f"Nama '{name}' sudah digunakan oleh barang lain!", "danger")
        return redirect(url_for('inventory.list_items'))

    item.name = name
    item.category_id = request.form.get('category_id')
    item.location_id = request.form.get('location_id')
    item.supplier_id = request.form.get('supplier_id')
    item.unit = request.form.get('unit')
    item.reorder_point = int(request.form.get('reorder_point', 0))
    item.notes = request.form.get('notes', '').strip()

    db.session.commit()
    flash(f"Data barang {item.item_code} berhasil diperbarui!", "success")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/items/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    item = MasterItem.query.get_or_404(id)
    item.deleted_at = datetime.utcnow() # Soft delete aman untuk audit histori
    db.session.commit()
    flash(f"Barang {item.name} berhasil dihapus dari sistem!", "warning")
    return redirect(url_for('inventory.list_items'))