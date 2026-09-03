from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.auth import auth_bp
from app.models import User
from app import db
from app.utils import roles_required

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Berhasil masuk!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Username atau password salah.', 'danger')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah keluar dari sistem.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/manage_users')
@login_required
@roles_required('Admin')
def manage_users():
    users = User.query.all()
    return render_template('auth/manage_users.html', users=users)

@auth_bp.route('/add_user', methods=['POST'])
@login_required
@roles_required('Admin')
def add_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    
    if User.query.filter_by(username=username).first():
        flash('Username sudah terdaftar!', 'danger')
    else:
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash(f'Pengguna {username} berhasil ditambahkan!', 'success')
        
    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/delete_user/<int:id>', methods=['POST'])
@login_required
@roles_required('Admin')
def delete_user(id):
    user_to_delete = User.query.get_or_404(id)
    if user_to_delete.id == current_user.id:
        flash('Anda tidak dapat menghapus akun Anda sendiri!', 'danger')
    else:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'Pengguna {user_to_delete.username} berhasil dihapus.', 'warning')
        
    return redirect(url_for('auth.manage_users'))