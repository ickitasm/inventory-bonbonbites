from app import create_app, db
# Pastikan import model User disesuaikan dengan isi app/models/__init__.py Anda
from app.models import User 
from werkzeug.security import generate_password_hash

# Inisialisasi aplikasi untuk mendapatkan application context
app = create_app()

def reset_database():
    with app.app_context():
        print("Memulai proses reset database Bonbonbites...")
        
        # 1. Menghapus semua tabel lama (Hati-hati: semua data akan hilang!)
        db.drop_all()
        print("[OK] Tabel lama berhasil dihapus.")
        
        # 2. Membuat ulang tabel berdasarkan skema terbaru di app/models/__init__.py
        db.create_all()
        print("[OK] Tabel baru berhasil dibuat (termasuk kolom 'role').")
        
        # 3. Menyuntikkan data pengguna awal (Seeding)
        print("Menambahkan data pengguna untuk keperluan testing...")
        
        # Buat akun Admin
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='Admin'
        )
        
        # Buat akun Manager
        manager_user = User(
            username='manager',
            password_hash=generate_password_hash('manager123'),
            role='Manager'
        )
        
        # Buat akun Staff / User
        staff_user = User(
            username='staff',
            password_hash=generate_password_hash('staff123'),
            role='Staff'
        )
        
        # Simpan ke database
        db.session.add_all([admin_user, manager_user, staff_user])
        db.session.commit()
        
        print("[OK] Data pengguna awal berhasil ditambahkan!")
        print("\n=== KREDENSIAL LOGIN ===")
        print("1. Superadmin/Admin -> Username: admin   | Password: admin123")
        print("2. Manager          -> Username: manager | Password: manager123")
        print("3. Staff            -> Username: staff   | Password: staff123")
        print("========================")

if __name__ == '__main__':
    reset_database()