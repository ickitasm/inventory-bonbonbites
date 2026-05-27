from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash # <-- Pastikan ini di-import
from app.auth import auth_bp
from app.models import User
from app import db

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login, langsung lempar ke dashboard
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Cari user di database
        user = User.query.filter_by(username=username).first()
        
        # Validasi user dan password
        if user and user.check_password(password):
            if not user.is_active:
                flash('Akun Anda telah dinonaktifkan.', 'danger')
                return redirect(url_for('auth.login'))
                
            login_user(user)
            flash(f'Selamat datang kembali, {user.username}!', 'success')
            
            # Jika user sebelumnya mencoba akses halaman lain sebelum login
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
            
        flash('Username atau password salah.', 'danger')
        
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah berhasil keluar dari sistem.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users', methods=['GET', 'POST'])
@login_required
def manage_users():
    # PROTEKSI: Hanya SUPERADMIN yang boleh masuk ke halaman ini
    if current_user.role != 'SUPERADMIN':
        flash('Akses Ditolak: Hanya Admin/Developer yang dapat mengelola pengguna.', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        role = request.form.get('role')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f'Username "{username}" sudah digunakan!', 'danger')
        else:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role=role
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'Pengguna baru {username} ({role}) berhasil ditambahkan!', 'success')
            
        return redirect(url_for('auth.manage_users'))
        
    users = User.query.all()
    return render_template('auth/manage_users.html', users=users)

@auth_bp.route('/users/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if current_user.role != 'SUPERADMIN':
        flash('Akses Ditolak.', 'danger')
        return redirect(url_for('dashboard.index'))
        
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('Anda tidak dapat menghapus akun Anda sendiri!', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'Pengguna {user.username} berhasil dihapus.', 'success')
        
    return redirect(url_for('auth.manage_users'))