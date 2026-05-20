from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
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