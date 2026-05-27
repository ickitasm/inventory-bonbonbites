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
    
    # Pastikan data yang kosong "" diubah menjadi None (NULL)
    cat_raw = request.form.get('category_id')
    loc_raw = request.form.get('location_id')
    sup_raw = request.form.get('supplier_id')
    
    category_id = int(cat_raw) if cat_raw else None
    location_id = int(loc_raw) if loc_raw else None
    supplier_id = int(sup_raw) if sup_raw else None
    
    unit = request.form.get('unit')
    reorder_point = request.form.get('reorder_point', 0)
    notes = request.form.get('notes', '').strip()

    # Validasi Unique Name
    existing_item = MasterItem.query.filter_by(name=name, deleted_at=None).first()
    if existing_item:
        flash(f"Barang dengan nama '{name}' sudah ada!", "danger")
        return redirect(url_for('inventory.list_items'))

    # Auto-generate SKU berdasarkan nama kategori objek
    prefix = "RAW"
    if category_id:
        cat_obj = Category.query.get(category_id)
        if cat_obj and cat_obj.name == "PACKAGING":
            prefix = "PKG"
    
    item_count = MasterItem.query.count() + 1
    item_code = f"{prefix}-{item_count:04d}"

    new_item = MasterItem(
        item_code=item_code,
        name=name,
        category_id=category_id,
        location_id=location_id,
        supplier_id=supplier_id,
        unit=unit,
        reorder_point=int(reorder_point) if reorder_point else 0,
        current_stock=0, 
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

    # Pastikan data yang kosong "" diubah menjadi None (NULL)
    cat_raw = request.form.get('category_id')
    loc_raw = request.form.get('location_id')
    sup_raw = request.form.get('supplier_id')

    item.name = name
    item.category_id = int(cat_raw) if cat_raw else None
    item.location_id = int(loc_raw) if loc_raw else None
    item.supplier_id = int(sup_raw) if sup_raw else None
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
    item.deleted_at = datetime.utcnow()
    db.session.commit()
    flash(f"Barang {item.name} berhasil dihapus dari sistem!", "warning")
    return redirect(url_for('inventory.list_items'))

@inventory_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')
        
        # --- LOGIKA TAMBAH DATA ---
        if action == 'add_category':
            name = request.form.get('name').strip().upper()
            if name and not Category.query.filter_by(name=name).first():
                db.session.add(Category(name=name))
                flash(f'Kategori {name} ditambahkan.', 'success')
                
        elif action == 'add_location':
            name = request.form.get('name').strip().upper()
            if name and not StorageLocation.query.filter_by(name=name).first():
                db.session.add(StorageLocation(name=name))
                flash(f'Lokasi {name} ditambahkan.', 'success')
                
        elif action == 'add_supplier':
            name = request.form.get('name').strip().upper()
            contact = request.form.get('contact_info').strip()
            if name and not Supplier.query.filter_by(name=name).first():
                db.session.add(Supplier(name=name, contact_info=contact))
                flash(f'Supplier {name} ditambahkan.', 'success')

        # --- LOGIKA HAPUS DATA (SAFE DELETE) ---
        elif action == 'delete_category':
            id = request.form.get('id')
            cat = Category.query.get(id)
            if cat:
                if cat.items: # Cek jika sedang dipakai barang
                    flash(f'Gagal: Kategori {cat.name} sedang digunakan oleh barang di Katalog!', 'danger')
                else:
                    db.session.delete(cat)
                    flash(f'Kategori {cat.name} berhasil dihapus.', 'success')

        elif action == 'delete_location':
            id = request.form.get('id')
            loc = StorageLocation.query.get(id)
            if loc:
                if loc.items:
                    flash(f'Gagal: Lokasi {loc.name} sedang digunakan oleh barang di Katalog!', 'danger')
                else:
                    db.session.delete(loc)
                    flash(f'Lokasi {loc.name} berhasil dihapus.', 'success')

        elif action == 'delete_supplier':
            id = request.form.get('id')
            sup = Supplier.query.get(id)
            if sup:
                if sup.primary_items or sup.price_list:
                    flash(f'Gagal: Supplier {sup.name} sedang digunakan oleh barang di Katalog!', 'danger')
                else:
                    db.session.delete(sup)
                    flash(f'Supplier {sup.name} berhasil dihapus.', 'success')
                
        db.session.commit()
        return redirect(url_for('inventory.settings'))

    categories = Category.query.all()
    locations = StorageLocation.query.all()
    suppliers = Supplier.query.all()
    
    return render_template(
        'inventory/settings.html', 
        categories=categories, 
        locations=locations, 
        suppliers=suppliers
    )