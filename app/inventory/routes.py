from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.inventory import inventory_bp
from app.models import MasterItem, Category, StorageLocation, Supplier, ActivityLog
from datetime import datetime

UNITS = ['GRAM', 'KG', 'PCS', 'PACK', 'KARTON', 'LITER', 'ML']

def log_activity(action, entity_type, entity_id, description):
    log = ActivityLog(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description
    )
    db.session.add(log)

@inventory_bp.route('/items')
@login_required
def list_items():
    items = MasterItem.query.filter_by(deleted_at=None).all()
    categories = Category.query.filter_by(is_active=True).all()
    locations = StorageLocation.query.filter_by(is_active=True).all()
    suppliers = Supplier.query.filter_by(is_active=True).all()
    
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
    item_name = request.form.get('name').strip()
    
    cat_raw = request.form.get('category_id')
    loc_raw = request.form.get('location_id')
    sup_raw = request.form.get('supplier_id')
    
    category_id = int(cat_raw) if cat_raw else None
    location_id = int(loc_raw) if loc_raw else None
    default_supplier_id = int(sup_raw) if sup_raw else None
    
    unit = request.form.get('unit')
    reorder_point = request.form.get('reorder_point', 0)
    notes = request.form.get('notes', '').strip()

    existing_item = MasterItem.query.filter_by(item_name=item_name, deleted_at=None).first()
    if existing_item:
        flash(f"Barang '{item_name}' sudah ada!", "danger")
        return redirect(url_for('inventory.list_items'))

    prefix = "RAW"
    if category_id:
        cat_obj = Category.query.get(category_id)
        if cat_obj and cat_obj.category_name == "PACKAGING":
            prefix = "PKG"
    
    item_count = MasterItem.query.count() + 1
    item_code = f"{prefix}-{item_count:04d}"

    new_item = MasterItem(
        item_code=item_code,
        item_name=item_name,
        category_id=category_id,
        storage_location_id=location_id,
        default_supplier_id=default_supplier_id,
        unit=unit,
        reorder_point=int(reorder_point) if reorder_point else 0,
        current_stock=0, 
        notes=notes
    )
    
    db.session.add(new_item)
    db.session.flush() # Dapatkan ID sebelum commit
    log_activity('CREATE', 'MASTER_ITEM', new_item.id, f"Menambahkan item baru: {item_code} - {item_name}")
    db.session.commit()
    
    flash(f"Barang {item_name} ({item_code}) berhasil didaftarkan!", "success")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/items/update/<int:id>', methods=['POST'])
@login_required
def update_item(id):
    item = MasterItem.query.get_or_404(id)
    item_name = request.form.get('name').strip()
    
    existing_item = MasterItem.query.filter(
        MasterItem.id != id, 
        MasterItem.item_name == item_name, 
        MasterItem.deleted_at == None
    ).first()
    
    if existing_item:
        flash(f"Nama '{item_name}' sudah digunakan!", "danger")
        return redirect(url_for('inventory.list_items'))

    item.item_name = item_name
    item.category_id = int(request.form.get('category_id')) if request.form.get('category_id') else None
    item.storage_location_id = int(request.form.get('location_id')) if request.form.get('location_id') else None
    item.default_supplier_id = int(request.form.get('supplier_id')) if request.form.get('supplier_id') else None
    item.unit = request.form.get('unit')
    item.reorder_point = int(request.form.get('reorder_point', 0))
    item.notes = request.form.get('notes', '').strip()

    log_activity('UPDATE', 'MASTER_ITEM', item.id, f"Memperbarui data item: {item.item_code}")
    db.session.commit()
    flash(f"Data barang {item.item_code} berhasil diperbarui!", "success")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/items/delete/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    item = MasterItem.query.get_or_404(id)
    item.deleted_at = datetime.utcnow()
    log_activity('DELETE', 'MASTER_ITEM', item.id, f"Menghapus (Soft Delete) item: {item.item_code}")
    db.session.commit()
    flash(f"Barang {item.item_name} berhasil dihapus dari sistem!", "warning")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        
        # --- TAMBAH DATA ---
        if action == 'add_category':
            name = request.form.get('name').strip().upper()
            if name and not Category.query.filter_by(category_name=name).first():
                new_cat = Category(category_name=name)
                db.session.add(new_cat)
                db.session.flush()
                log_activity('CREATE', 'CATEGORY', new_cat.id, f"Kategori baru: {name}")
                flash(f'Kategori {name} ditambahkan.', 'success')
                
        elif action == 'add_location':
            name = request.form.get('name').strip().upper()
            if name and not StorageLocation.query.filter_by(location_code=name).first():
                new_loc = StorageLocation(location_code=name, description="Added from settings")
                db.session.add(new_loc)
                db.session.flush()
                log_activity('CREATE', 'LOCATION', new_loc.id, f"Lokasi baru: {name}")
                flash(f'Lokasi {name} ditambahkan.', 'success')
                
        elif action == 'add_supplier':
            name = request.form.get('name').strip().upper()
            contact = request.form.get('contact_info').strip()
            if name and not Supplier.query.filter_by(supplier_name=name).first():
                new_sup = Supplier(supplier_name=name, contact=contact)
                db.session.add(new_sup)
                db.session.flush()
                log_activity('CREATE', 'SUPPLIER', new_sup.id, f"Supplier baru: {name}")
                flash(f'Supplier {name} ditambahkan.', 'success')

        # --- HAPUS DATA (SOFT DISABLE) ---
        elif action == 'delete_category':
            id = request.form.get('id')
            cat = Category.query.get(id)
            if cat:
                cat.is_active = False
                log_activity('DISABLE', 'CATEGORY', id, f"Menonaktifkan kategori: {cat.category_name}")
                flash(f'Kategori {cat.category_name} berhasil dinonaktifkan.', 'warning')

        elif action == 'delete_location':
            id = request.form.get('id')
            loc = StorageLocation.query.get(id)
            if loc:
                loc.is_active = False
                log_activity('DISABLE', 'LOCATION', id, f"Menonaktifkan lokasi: {loc.location_code}")
                flash(f'Lokasi {loc.location_code} berhasil dinonaktifkan.', 'warning')

        elif action == 'delete_supplier':
            id = request.form.get('id')
            sup = Supplier.query.get(id)
            if sup:
                sup.is_active = False
                log_activity('DISABLE', 'SUPPLIER', id, f"Menonaktifkan supplier: {sup.supplier_name}")
                flash(f'Supplier {sup.supplier_name} berhasil dinonaktifkan.', 'warning')

        # --- AKTIFKAN KEMBALI (RESTORE) ---
        elif action == 'restore_category':
            id = request.form.get('id')
            cat = Category.query.get(id)
            if cat:
                cat.is_active = True
                log_activity('RESTORE', 'CATEGORY', id, f"Mengaktifkan kategori: {cat.category_name}")
                flash(f'Kategori {cat.category_name} diaktifkan kembali.', 'success')

        elif action == 'restore_location':
            id = request.form.get('id')
            loc = StorageLocation.query.get(id)
            if loc:
                loc.is_active = True
                log_activity('RESTORE', 'LOCATION', id, f"Mengaktifkan lokasi: {loc.location_code}")
                flash(f'Lokasi {loc.location_code} diaktifkan kembali.', 'success')

        elif action == 'restore_supplier':
            id = request.form.get('id')
            sup = Supplier.query.get(id)
            if sup:
                sup.is_active = True
                log_activity('RESTORE', 'SUPPLIER', id, f"Mengaktifkan supplier: {sup.supplier_name}")
                flash(f'Supplier {sup.supplier_name} diaktifkan kembali.', 'success')
                
        db.session.commit()
        return redirect(url_for('inventory.settings'))

    # Ubah menjadi .all() agar data yang Nonaktif tetap muncul di layar Settings
    categories = Category.query.all()
    locations = StorageLocation.query.all()
    suppliers = Supplier.query.all()
    
    return render_template(
        'inventory/settings.html', 
        categories=categories, 
        locations=locations, 
        suppliers=suppliers
    )