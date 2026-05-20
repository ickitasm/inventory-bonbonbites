import os
from dotenv import load_dotenv

# Ambil direktori dasar proyek
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Digunakan oleh Flask-Login dan Session Cookie untuk enkripsi data
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-default-for-dev'
    
    # Konfigurasi MySQL Connection
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://root:@localhost/db_inventory_ledger'
    
    # Mematikan fitur tracker bawaan SQLAlchemy yang memakan banyak memori RAM
    SQLALCHEMY_TRACK_MODIFICATIONS = False