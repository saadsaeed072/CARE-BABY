from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from extensions import mysql
from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required

auth_bp = Blueprint('auth', __name__)

#AUTHENTICATION ROUTES

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        
        # Validate required fields
        if not full_name or not email or not phone or not password or not city:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validate user_type (prevent admin injection)
        if user_type not in ['parent', 'babysitter']:
            flash('Invalid account type.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validate email format
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validate phone format
        if not is_valid_phone(phone):
            flash('Please enter a valid phone number (e.g. 03001234567).', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return redirect(url_for('auth.register'))
        
        cur = get_db_connection()
        
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'danger')
            cur.close()
            return redirect(url_for('auth.register'))
        
        password_hash = generate_password_hash(password)
        
        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, phone, city, address, user_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (email, password_hash, full_name, phone, city, address, user_type))
        
        user_id = cur.lastrowid
        
        if user_type == 'parent':
            cur.execute("""
                INSERT INTO parent_profiles (user_id, family_name)
                VALUES (%s, %s)
            """, (user_id, full_name))
        elif user_type == 'babysitter':
            cur.execute("""
                INSERT INTO babysitter_profiles (user_id)
                VALUES (%s)
            """, (user_id,))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password')
        
        # Validate required fields
        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('auth/login.html')
        
        cur = get_db_connection()
        cur.execute("SELECT * FROM users WHERE email = %s AND is_active = TRUE", (email,))
        user = cur.fetchone()
        cur.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            session['user_name'] = user['full_name']
            session['user_email'] = user['email']
            
            cur = get_db_connection()
            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            mysql.connection.commit()
            cur.close()
            
            flash(f'Welcome back, {user["full_name"]}!', 'success')
            
            if user['user_type'] == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            elif user['user_type'] == 'babysitter':
                return redirect(url_for('babysitter.babysitter_dashboard'))
            else:
                return redirect(url_for('parent.parent_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))

