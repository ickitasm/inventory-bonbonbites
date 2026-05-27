from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 1. MODEL USER (Aktor Sistem)
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='MANAGER')
    
    # Relasi
    snapshots = db.relationship('StockSnapshot', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. MODEL MASTER PENDUKUNG (Kategori, Lokasi, Supplier)
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    items = db.relationship('MasterItem', backref='category_rel', lazy=True)

class StorageLocation(db.Model):
    __tablename__ = 'storage_locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    items = db.relationship('MasterItem', backref='location_rel', lazy=True)

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Relasi
    primary_items = db.relationship('MasterItem', backref='primary_supplier', lazy=True)
    price_list = db.relationship('ItemSupplierPrice', backref='supplier_rel', lazy=True)

# 3. MODEL MASTER ITEM (Core Catalog)
class MasterItem(db.Model):
    __tablename__ = 'master_items'
    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    # FK Pendukung (Menggantikan kolom teks biasa)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    location_id = db.Column(db.Integer, db.ForeignKey('storage_locations.id'), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True) # Supplier Utama
    
    unit = db.Column(db.String(20))
    reorder_point = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0) 
    notes = db.Column(db.Text, nullable=True) # Catatan barang
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relasi ke Snapshot & Harga Supplier Alternatif
    snapshots = db.relationship('StockSnapshot', backref='item', lazy=True)
    supplier_prices = db.relationship('ItemSupplierPrice', backref='item_rel', lazy=True, cascade="all, delete-orphan")

# 4. MODEL HARGA ALTERNATIF SUPPLIER (Supplier Reference Lite)
class ItemSupplierPrice(db.Model):
    __tablename__ = 'item_supplier_prices'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('master_items.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 5. MODEL STOCK SNAPSHOT (Tabel Transaksional Vertikal - Core Argument)
class StockSnapshot(db.Model):
    __tablename__ = 'stock_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('master_items.id'), nullable=False)
    actual_qty = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    snapshot_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)