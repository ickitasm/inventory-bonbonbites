from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.auth import auth_bp
from app.models import User
from app import db
from functools import wraps
from app.utils import roles_required



@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Selamat datang kembali, {user.full_name or user.username}!', 'success')
            return redirect(url_for('dashboard.index'))
            
        flash('Username tidak ditemukan atau password salah!', 'danger')
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah berhasil keluar dari sistem.', 'info')
    return redirect(url_for('auth.login'))


def roles_required(*roles):
    """
    Decorator untuk membatasi akses berdasarkan role pengguna.
    Jika role pengguna tidak ada dalam daftar 'roles', kembalikan error 403 Forbidden.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/users', methods=['GET', 'POST'])
@login_required
@roles_required('Admin')
def manage_users():
    if current_user.role != 'SUPERADMIN':
        flash('Akses Ditolak: Hanya Superadmin yang dapat mengelola pengguna.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username').strip()
        
        # Penanganan aman untuk full_name
        full_name_raw = request.form.get('full_name')
        full_name = full_name_raw.strip() if full_name_raw else username
        
        password = request.form.get('password')
        role = request.form.get('role')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f'Username "{username}" sudah digunakan!', 'danger')
        else:
            new_user = User(
                username=username,
                full_name=full_name,
                password_hash=generate_password_hash(password),
                role=role,
                is_active=True
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Pengguna baru {username} berhasil ditambahkan!', 'success')
            
        return redirect(url_for('auth.manage_users'))
        
    users = User.query.all()
    return render_template('auth/manage_users.html', users=users)
pass

@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'SUPERADMIN':
        flash('Akses Ditolak.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Anda tidak dapat menghapus/menonaktifkan akun Anda sendiri!', 'danger')
    else:
        # Menggunakan Soft Delete (is_active = False) agar histori opnamenya tidak error
        user.is_active = False 
        db.session.commit()
        flash(f'Pengguna {user.username} berhasil dinonaktifkan.', 'success')
        
    return redirect(url_for('auth.manage_users'))