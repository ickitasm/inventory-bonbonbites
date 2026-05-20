from app import create_app, db
from app.models import User  # <--- Hapus UserRole dari sini
from werkzeug.security import generate_password_hash

app = create_app()

@app.cli.command("seed-admin")
def seed_admin():
    """Suntik user admin pertama kali ke database."""
    # Cek apakah user admin sudah ada
    admin = User.query.filter_by(username="admin123").first()
    if not admin:
        hashed_password = generate_password_hash("admin123")
        # Role langsung diisi string 'SUPERADMIN' sesuai model baru
        admin_user = User(username="admin123", password_hash=hashed_password, role="SUPERADMIN")
        db.session.add(admin_user)
        db.session.commit()
        print("Selesai: Akun admin123 berhasil dibuat!")
    else:
        print("Info: Akun admin123 sudah ada.")

if __name__ == "__main__":
    app.run(debug=True)