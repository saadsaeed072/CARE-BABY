from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from extensions import mysql, limiter, mail
from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Message
import random
import string

auth_bp = Blueprint('auth', __name__)


def get_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def send_verification_email(user_email, user_name, token):
    """Send email verification link. Returns True on success, False on failure."""
    verify_url = url_for('auth.confirm_email', token=token, _external=True)
    mail_username = current_app.config.get('MAIL_USERNAME', '')

    if not mail_username:
        # Dev fallback: print to console instead of sending email
        print("\n" + "="*60)
        print("📧 EMAIL VERIFICATION (DEV MODE - No SMTP configured)")
        print(f"   To: {user_email} ({user_name})")
        print(f"   Link: {verify_url}")
        print("="*60 + "\n")
        return False

    try:
        msg = Message(
            subject="Verify Your BabyCare Email Address",
            recipients=[user_email],
            html=render_template('auth/verification_email.html',
                                 user_name=user_name,
                                 verify_url=verify_url)
        )
        mail.send(msg)
        print(f"[EMAIL OK] Verification email sent to {user_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send verification email to {user_email}: {e}")
        print(f"   Fallback verify link: {verify_url}")
        return False


# ─── REGISTER ────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
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

        # Server‑side length checks
        if len(full_name) > 30:
            flash('Full name must be 30 characters or fewer.', 'danger')
            return redirect(url_for('auth.register'))
        if not full_name.replace(' ', '').isalpha():
            flash('Full name must contain only letters and spaces.', 'danger')
            return redirect(url_for('auth.register'))
        if len(email) > 100:
            flash('Email must be 100 characters or fewer.', 'danger')
            return redirect(url_for('auth.register'))
        if len(phone) > 11:
            flash('Phone number must be 11 digits.', 'danger')
            return redirect(url_for('auth.register'))
        if len(address) > 250:
            flash('Address must be 250 characters or fewer.', 'danger')
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

        if len(password) > 30:
            flash('Password must be between 8 and 30 characters long.', 'danger')
            return redirect(url_for('auth.register'))

        cur = get_db_connection()

        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'danger')
            cur.close()
            return redirect(url_for('auth.register'))

        password_hash = generate_password_hash(password)

        # Generate verification token
        token = get_serializer().dumps(email, salt='email-verification')

        cur.execute("""
            INSERT INTO users (email, password_hash, full_name, phone, city, address, user_type,
                               is_email_verified, email_verification_token, email_verification_sent_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, %s, NOW())
        """, (email, password_hash, full_name, phone, city, address, user_type, token))

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

        # Send verification email
        email_sent = send_verification_email(email, full_name, token)

        if email_sent:
            flash(
                f'Registration successful! A verification email has been sent to <strong>{email}</strong>. '
                'Please check your inbox (and Spam/Promotions folder) to verify your account.',
                'success'
            )
        else:
            # Email failed — give user the direct link so they can still verify
            verify_url = url_for('auth.confirm_email', token=token, _external=True)
            flash(
                f'Registration successful! However, we could not send the verification email to <strong>{email}</strong>. '
                f'Please <a href="{verify_url}">click here to verify your account now</a>, '
                'or try <a href="' + url_for('auth.resend_verification') + '">resending the verification email</a> later.',
                'warning'
            )
        return redirect(url_for('auth.login'))


    return render_template('auth/register.html')


# ─── CONFIRM EMAIL ────────────────────────────────────────────────────────────

@auth_bp.route('/verify-email/<token>')
def confirm_email(token):
    try:
        email = get_serializer().loads(token, salt='email-verification', max_age=86400)  # 24 hours
    except SignatureExpired:
        flash('The verification link has expired (valid for 24 hours). Please register again or contact support.', 'danger')
        return redirect(url_for('auth.login'))
    except BadTimeSignature:
        flash('The verification link is invalid. Please register again.', 'danger')
        return redirect(url_for('auth.login'))

    cur = get_db_connection()
    cur.execute("SELECT id, full_name, is_email_verified FROM users WHERE email = %s", (email,))
    user = cur.fetchone()

    if not user:
        flash('User not found.', 'danger')
        cur.close()
        return redirect(url_for('auth.login'))

    if user['is_email_verified']:
        flash('Your email is already verified. Please log in.', 'info')
        cur.close()
        return redirect(url_for('auth.login'))

    cur.execute("""
        UPDATE users SET is_email_verified = TRUE, email_verification_token = NULL
        WHERE email = %s
    """, (email,))
    mysql.connection.commit()
    cur.close()

    flash(f'Email verified successfully! Welcome, {user["full_name"]}. You can now log in.', 'success')
    return redirect(url_for('auth.login'))


# ─── RESEND VERIFICATION ──────────────────────────────────────────────────────

@auth_bp.route('/resend-verification', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def resend_verification():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('auth.resend_verification'))

        cur = get_db_connection()
        cur.execute("SELECT id, full_name, is_email_verified FROM users WHERE email = %s AND is_active = TRUE", (email,))
        user = cur.fetchone()

        if not user:
            # Don't reveal whether email exists
            flash('If that email is registered, a new verification link has been sent.', 'info')
            cur.close()
            return redirect(url_for('auth.login'))

        if user['is_email_verified']:
            flash('Your email is already verified. Please log in.', 'info')
            cur.close()
            return redirect(url_for('auth.login'))

        token = get_serializer().dumps(email, salt='email-verification')
        cur.execute("""
            UPDATE users SET email_verification_token = %s, email_verification_sent_at = NOW()
            WHERE email = %s
        """, (token, email))
        mysql.connection.commit()
        cur.close()

        send_verification_email(email, user['full_name'], token)
        flash('A new verification email has been sent. Please check your inbox.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/resend_verification.html')


# ─── LOGIN ────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
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
            # Admins are pre-verified; all other users must verify their email
            is_admin = user.get('user_type') == 'admin'
            if not is_admin and not user.get('is_email_verified'):
                flash(
                    'Please verify your email address before logging in. '
                    '<a href="' + url_for('auth.resend_verification') + '">Resend verification email</a>',
                    'warning'
                )
                return render_template('auth/login.html')

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


# ─── LOGOUT ───────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))


# ─── FORGOT PASSWORD ──────────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        cur = get_db_connection()
        cur.execute("SELECT id, full_name FROM users WHERE email = %s AND is_active = TRUE", (email,))
        user = cur.fetchone()

        if user:
            # Generate 6-digit code
            reset_code = ''.join(random.choices(string.digits, k=6))
            # Set expiry (15 minutes)
            expires_at = datetime.now() + timedelta(minutes=15)

            cur.execute("""
                UPDATE users SET reset_code = %s, reset_code_expires_at = %s
                WHERE id = %s
            """, (reset_code, expires_at, user['id']))
            mysql.connection.commit()

            # Send email
            try:
                msg = Message(
                    subject="Your Password Reset Code - BabyCare",
                    recipients=[email],
                    html=render_template('emails/reset_password_code.html',
                                         user_name=user['full_name'],
                                         reset_code=reset_code)
                )
                mail.send(msg)
            except Exception as e:
                print(f"[EMAIL ERROR] Could not send reset email: {e}")
                # We don't flash error here to keep the flow identical
        
        # Always flash success and redirect to reset-password to prevent user enumeration
        flash('If that email is registered, a 6-digit reset code has been sent.', 'success')
        session['reset_email'] = email
        cur.close()
        return redirect(url_for('auth.reset_password'))

    return render_template('auth/forgot_password.html')


# ─── RESET PASSWORD ───────────────────────────────────────────────────────────

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def reset_password():
    email = session.get('reset_email')
    if not email:
        flash('Please request a reset code first.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not code or not new_password or not confirm_password:
            flash('Please fill in all fields.', 'danger')
            return render_template('auth/reset_password.html')

        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/reset_password.html')

        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('auth/reset_password.html')

        cur = get_db_connection()
        cur.execute("""
            SELECT id FROM users 
            WHERE email = %s AND reset_code = %s AND reset_code_expires_at > NOW()
        """, (email, code))
        user = cur.fetchone()

        if user:
            password_hash = generate_password_hash(new_password)
            cur.execute("""
                UPDATE users 
                SET password_hash = %s, reset_code = NULL, reset_code_expires_at = NULL 
                WHERE id = %s
            """, (password_hash, user['id']))
            mysql.connection.commit()
            cur.close()
            
            session.pop('reset_email', None)
            flash('Your password has been reset successfully. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired reset code.', 'danger')
            cur.close()

    return render_template('auth/reset_password.html')
