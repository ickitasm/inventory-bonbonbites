from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Tolak jika belum login
            if not current_user.is_authenticated:
                abort(403)
            
            # Cegah error jika kolom role di DB masih NULL
            user_role = current_user.role if current_user.role else ""
            
            # Ubah semua ke huruf kecil agar kebal typo ('Admin' == 'admin')
            allowed_roles = [r.lower() for r in roles]
            
            if user_role.lower() not in allowed_roles:
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator