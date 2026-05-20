from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

# Inisialisasi extension secara global
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Hubungkan extension ke instance aplikasi
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Konfigurasi Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu untuk mengakses halaman ini.'
    login_manager.login_message_category = 'warning'

    # Register Blueprints
    from app.auth import auth_bp
    from app.inventory import inventory_bp
    from app.dashboard import dashboard_bp
    from app.snapshot.routes import snapshot_bp  # <--- TAMBAHKAN INI

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(snapshot_bp, url_prefix='/snapshot') # <--- TAMBAHKAN INI

    # Jalur utama otomatis membelokkan user ke halaman yang tepat
    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('auth.login'))

    # PASTIKAN BARIS INI ADA DI SINI (Sejajar dengan db.init_app di atas)
    return app

# WAJIB DI SINI: Di luar fungsi agar Alembic bisa membaca semua model tabel
from app import models

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))