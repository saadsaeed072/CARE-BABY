import re
from functools import wraps
from flask import session, flash, redirect, url_for
from extensions import mysql

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone):
    pattern = r'^(\+92|0)[0-9]{10}$'
    cleaned = re.sub(r'[\s\-]', '', phone)
    return re.match(pattern, cleaned) is not None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('user_type') not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                if session.get('user_type') == 'admin':
                    return redirect(url_for('admin.admin_dashboard'))
                elif session.get('user_type') == 'parent':
                    return redirect(url_for('parent.parent_dashboard'))
                elif session.get('user_type') == 'babysitter':
                    return redirect(url_for('babysitter.babysitter_dashboard'))
                else:
                    return redirect(url_for('public.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_db_connection():
    return mysql.connection.cursor()
