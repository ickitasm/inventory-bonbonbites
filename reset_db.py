from run import app
from app import db
from app.models import (
    ActivityLog, StockSnapshot, StockOpnameSession,
    ItemSupplierPrice, MasterItem, Supplier,
    StorageLocation, Category, User
)

def reset_database():
    with app.app_context():
        print("⏳ Memulai proses pembersihan database...")
        try:
            # 1. Hapus data Histori & Log (Child)
            print("Menghapus Activity Log...")
            db.session.query(ActivityLog).delete()
            
            print("Menghapus Data Stock Opname...")
            db.session.query(StockSnapshot).delete()
            db.session.query(StockOpnameSession).delete()
            
            # 2. Hapus data Master Item dan Harga Supplier (Child dari data Pendukung)
            print("Menghapus Master Item & Harga...")
            db.session.query(ItemSupplierPrice).delete()
            db.session.query(MasterItem).delete()
            
            # 3. Hapus data Pendukung / Settings (Parent)
            print("Menghapus Kategori, Lokasi, dan Supplier...")
            db.session.query(Category).delete()
            db.session.query(StorageLocation).delete()
            db.session.query(Supplier).delete()
            
            # Eksekusi penghapusan di database
            db.session.commit()
            print("✅ SUKSES: Data Riwayat, Master Item, dan Data Pendukung berhasil direset!")
            
            # Pengecekan akun User
            admin_count = User.query.count()
            print(f"ℹ️ Akun User yang tersisa di sistem: {admin_count} akun.")
            
        except Exception as e:
            # Batalkan jika ada error
            db.session.rollback()
            print(f"❌ GAGAL: Terjadi kesalahan -> {e}")

if __name__ == '__main__':
    # Meminta konfirmasi sebelum menghapus
    konfirmasi = input("Yakin ingin menghapus semua data inventori? (y/n): ")
    if konfirmasi.lower() == 'y':
        reset_database()
    else:
        print("Proses reset dibatalkan.")