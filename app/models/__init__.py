from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 1. MODEL USER
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=True) # NEW
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='MANAGER')
    is_active = db.Column(db.Boolean, default=True) # NEW
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # NEW
    
    # Relasi
    opname_sessions = db.relationship('StockOpnameSession', backref='author', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user_rel', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. MODEL MASTER KATEGORI
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    category_name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True) # NEW
    is_active = db.Column(db.Boolean, default=True) # NEW
    
    items = db.relationship('MasterItem', backref='category_rel', lazy=True)

# 3. MODEL MASTER LOKASI (Diperkaya)
class StorageLocation(db.Model):
    __tablename__ = 'storage_locations'
    id = db.Column(db.Integer, primary_key=True)
    floor_code = db.Column(db.String(20), nullable=True) # NEW (e.g., LT1)
    storage_type = db.Column(db.String(50), nullable=True) # NEW (e.g., RACK, FREEZER)
    location_code = db.Column(db.String(50), unique=True, nullable=False) # NEW (e.g., LT1-RACK-A1)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    items = db.relationship('MasterItem', backref='location_rel', lazy=True)

# 4. MODEL MASTER SUPPLIER
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    supplier_name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True) # NEW
    supplier_code = db.Column(db.String(50), unique=True, nullable=True) # NEW
    is_active = db.Column(db.Boolean, default=True) # NEW
    
    primary_items = db.relationship('MasterItem', backref='default_supplier', lazy=True)
    price_list = db.relationship('ItemSupplierPrice', backref='supplier_rel', lazy=True)

# 5. MODEL MASTER ITEM (Katalog Utama)
class MasterItem(db.Model):
    __tablename__ = 'master_items'
    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(20), unique=True, nullable=False) # SKU
    item_name = db.Column(db.String(100), nullable=False)
    
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    storage_location_id = db.Column(db.Integer, db.ForeignKey('storage_locations.id'), nullable=True)
    default_supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    
    unit = db.Column(db.String(20))
    reorder_point = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0) 
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    supplier_prices = db.relationship('ItemSupplierPrice', backref='item_rel', lazy=True, cascade="all, delete-orphan")
    snapshots = db.relationship('StockSnapshot', backref='item', lazy=True)

# 6. MODEL HARGA SUPPLIER ALTERNATIF
class ItemSupplierPrice(db.Model):
    __tablename__ = 'item_supplier_prices'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('master_items.id'), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    
    purchase_price = db.Column(db.Numeric(12, 2), nullable=False)
    is_default = db.Column(db.Boolean, default=False) # NEW
    effective_date = db.Column(db.Date, nullable=True) # NEW
    notes = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 7. MODEL STOCK OPNAME SESSIONS (HEADER - NEW)
class StockOpnameSession(db.Model):
    __tablename__ = 'stock_opname_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_code = db.Column(db.String(50), unique=True, nullable=False) # e.g., OP-20260528-001
    session_datetime = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='COMPLETED') # e.g., DRAFT, COMPLETED
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    snapshots = db.relationship('StockSnapshot', backref='session_rel', lazy=True, cascade="all, delete-orphan")

# 8. MODEL STOCK SNAPSHOTS (DETAIL - UPDATED)
class StockSnapshot(db.Model):
    __tablename__ = 'stock_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('stock_opname_sessions.id'), nullable=False) # NEW FK Header
    item_id = db.Column(db.Integer, db.ForeignKey('master_items.id'), nullable=False)
    
    physical_qty = db.Column(db.Integer, nullable=False)
    system_qty_before = db.Column(db.Integer, nullable=False) # NEW (Stok sebelum opname)
    variance_qty = db.Column(db.Integer, nullable=False) # NEW (Selisih: physical - system)
    
    notes = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 9. MODEL ACTIVITY LOGS (AUDIT TRAIL - NEW)
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False) # e.g., CREATE, UPDATE, DELETE, OPNAME
    entity_type = db.Column(db.String(50), nullable=False) # e.g., MASTER_ITEM, CATEGORY
    entity_id = db.Column(db.Integer, nullable=True) # ID dari data yang diubah
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)