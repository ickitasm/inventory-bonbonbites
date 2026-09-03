from app import create_app, db
from app.models import User 
from werkzeug.security import generate_password_hash

app = create_app()

def reset_database():
    with app.app_context():
        db.drop_all()
        db.create_all()
        
        # Buat akun Admin
        admin_user = User(username='admin', password_hash=generate_password_hash('admin123'), role='Admin')
        
        # Buat akun Manager
        manager_user = User(username='manager', password_hash=generate_password_hash('manager123'), role='Manager')
        
        # Buat akun Staff
        staff_user = User(username='staff', password_hash=generate_password_hash('staff123'), role='Staff')
        
        db.session.add_all([admin_user, manager_user, staff_user])
        db.session.commit()
        print("Database berhasil di-reset dengan role Admin, Manager, dan Staff.")

if __name__ == '__main__':
    reset_database()