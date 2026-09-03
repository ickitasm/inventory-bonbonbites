from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            
            # Ambil role user, jadikan huruf kecil semua
            user_role = current_user.role.lower() if current_user.role else ""
            allowed_roles = [r.lower() for r in roles]
            
            # Cek apakah role user ada di daftar yang diizinkan
            if user_role not in allowed_roles:
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator