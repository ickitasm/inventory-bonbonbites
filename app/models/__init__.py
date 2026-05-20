from datetime import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# 1. MODEL USER
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='STAFF')
    
    # Relasi
    snapshots = db.relationship('StockSnapshot', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 2. MODEL MASTER ITEM
class MasterItem(db.Model):
    __tablename__ = 'master_items'
    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20))
    reorder_point = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relasi ke Snapshot
    snapshots = db.relationship('StockSnapshot', backref='item', lazy=True)

# 3. MODEL STOCK SNAPSHOT
class StockSnapshot(db.Model):
    __tablename__ = 'stock_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('master_items.id'), nullable=False)
    actual_qty = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    snapshot_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)