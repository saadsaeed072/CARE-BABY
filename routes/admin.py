from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from extensions import mysql
from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required

admin_bp = Blueprint('admin', __name__)

#ADMIN ROUTES

@admin_bp.route('/admin/dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    cur = get_db_connection()
    
    cur.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'parent'")
    total_parents = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'babysitter'")
    total_babysitters = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM bookings")
    total_bookings = cur.fetchone()['count']
    
    cur.execute("""
        SELECT COALESCE(SUM(platform_fee), 0) as total_revenue
        FROM bookings WHERE status = 'completed'
    """)
    total_revenue = cur.fetchone()['total_revenue']
    
    cur.execute("""
        SELECT u.id, u.full_name, u.email, u.phone, u.city, u.created_at,
               bp.verification_status, bp.cnic_number
        FROM users u
        JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE bp.verification_status = 'pending'
        ORDER BY u.created_at DESC
        LIMIT 10
    """)
    pending_verifications = cur.fetchall()
    
    cur.execute("""
        SELECT b.*, u.full_name as parent_name,
               (SELECT u2.full_name FROM users u2 
                JOIN babysitter_profiles bp2 ON u2.id = bp2.user_id 
                WHERE bp2.id = b.babysitter_id) as sitter_name
        FROM bookings b
        JOIN users u ON b.parent_id = u.id
        ORDER BY b.created_at DESC
        LIMIT 10
    """)
    recent_bookings = cur.fetchall()
    
    cur.execute("""
        SELECT wr.*, u.full_name as sitter_name
        FROM withdrawal_requests wr
        JOIN babysitter_profiles bp ON wr.babysitter_id = bp.id
        JOIN users u ON bp.user_id = u.id
        WHERE wr.status = 'pending'
        ORDER BY wr.requested_at DESC
    """)
    pending_withdrawals = cur.fetchall()
    
    cur.close()
    
    return render_template('admin/dashboard.html',
                         total_parents=total_parents,
                         total_babysitters=total_babysitters,
                         total_bookings=total_bookings,
                         total_revenue=total_revenue,
                         pending_verifications=pending_verifications,
                         recent_bookings=recent_bookings,
                         pending_withdrawals=pending_withdrawals)

@admin_bp.route('/admin/users')
@login_required
@role_required(['admin'])
def admin_users():
    cur = get_db_connection()
    
    user_type = request.args.get('type', 'all')
    status = request.args.get('status', 'all')
    
    query = "SELECT * FROM users WHERE 1=1"
    params = []
    
    if user_type != 'all':
        query += " AND user_type = %s"
        params.append(user_type)
    
    if status == 'active':
        query += " AND is_active = TRUE"
    elif status == 'inactive':
        query += " AND is_active = FALSE"
    
    query += " ORDER BY created_at DESC"
    
    cur.execute(query, params)
    users = cur.fetchall()
    cur.close()
    
    return render_template('admin/users.html', users=users, user_type=user_type, status=status)

@admin_bp.route('/admin/user/<int:user_id>/<action>')
@login_required
@role_required(['admin'])
def admin_user_action(user_id, action):
    cur = get_db_connection()
    
    if action not in ['activate', 'deactivate', 'verify']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin.admin_users'))
        
    if action == 'activate':
        cur.execute("UPDATE users SET is_active = TRUE WHERE id = %s", (user_id,))
        flash('User activated successfully.', 'success')
    elif action == 'deactivate':
        cur.execute("UPDATE users SET is_active = FALSE WHERE id = %s", (user_id,))
        flash('User deactivated successfully.', 'success')
    elif action == 'verify':
        cur.execute("UPDATE users SET is_verified = TRUE WHERE id = %s", (user_id,))
        flash('User verified successfully.', 'success')
    
    cur.execute("""
        INSERT INTO admin_logs (admin_id, action, target_type, target_id, details)
        VALUES (%s, %s, 'user', %s, %s)
    """, (session['user_id'], action, user_id, f'User {action}d'))
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/admin/verifications')
@login_required
@role_required(['admin'])
def admin_verifications():
    cur = get_db_connection()
    
    cur.execute("""
        SELECT u.id, u.full_name, u.email, u.phone, u.city, u.created_at,
               bp.id as profile_id, bp.verification_status, bp.cnic_number,
               bp.cnic_front_image, bp.cnic_back_image, bp.background_check_status
        FROM users u
        JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE bp.verification_status IN ('pending', 'unverified')
        ORDER BY 
            CASE bp.verification_status WHEN 'pending' THEN 0 ELSE 1 END,
            u.created_at DESC
    """)
    verifications = cur.fetchall()
    cur.close()
    
    return render_template('admin/verifications.html', verifications=verifications)

@admin_bp.route('/admin/verification/<int:profile_id>/<action>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_verify_profile(profile_id, action):
    notes = request.form.get('notes', '')
    
    cur = get_db_connection()
    
    if action not in ['approve', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin.admin_verifications'))
        
    if action == 'approve':
        cur.execute("""
            UPDATE babysitter_profiles 
            SET verification_status = 'verified', background_check_status = 'approved'
            WHERE id = %s
        """, (profile_id,))
        
        cur.execute("""
            UPDATE users SET is_verified = TRUE
            WHERE id = (SELECT user_id FROM babysitter_profiles WHERE id = %s)
        """, (profile_id,))
        
        flash('Verification approved successfully.', 'success')
    elif action == 'reject':
        cur.execute("""
            UPDATE babysitter_profiles 
            SET verification_status = 'rejected', background_check_notes = %s
            WHERE id = %s
        """, (notes, profile_id))
        flash('Verification rejected.', 'warning')
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('admin.admin_verifications'))

@admin_bp.route('/admin/bookings')
@login_required
@role_required(['admin'])
def admin_bookings():
    cur = get_db_connection()
    
    status_filter = request.args.get('status', 'all')
    
    query = """
        SELECT b.*, u.full_name as parent_name,
               (SELECT u2.full_name FROM users u2 
                JOIN babysitter_profiles bp2 ON u2.id = bp2.user_id 
                WHERE bp2.id = b.babysitter_id) as sitter_name
        FROM bookings b
        JOIN users u ON b.parent_id = u.id
    """
    params = []
    
    if status_filter != 'all':
        query += " WHERE b.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY b.created_at DESC"
    
    cur.execute(query, params)
    bookings = cur.fetchall()
    cur.close()
    
    return render_template('admin/bookings.html', bookings=bookings, status_filter=status_filter)

@admin_bp.route('/admin/withdrawals')
@login_required
@role_required(['admin'])
def admin_withdrawals():
    cur = get_db_connection()
    
    status_filter = request.args.get('status', 'pending')
    
    query = """
        SELECT wr.*, u.full_name as sitter_name, u.email as sitter_email
        FROM withdrawal_requests wr
        JOIN babysitter_profiles bp ON wr.babysitter_id = bp.id
        JOIN users u ON bp.user_id = u.id
    """
    params = []
    
    if status_filter != 'all':
        query += " WHERE wr.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY wr.requested_at DESC"
    
    cur.execute(query, params)
    withdrawals = cur.fetchall()
    cur.close()
    
    return render_template('admin/withdrawals.html', withdrawals=withdrawals, status_filter=status_filter)

@admin_bp.route('/admin/withdrawal/<int:withdrawal_id>/<action>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_process_withdrawal(withdrawal_id, action):
    notes = request.form.get('notes', '')
    
    cur = get_db_connection()
    
    if action not in ['approve', 'reject', 'complete']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin.admin_withdrawals'))
        
    if action == 'approve':
        cur.execute("""
            UPDATE withdrawal_requests 
            SET status = 'approved', admin_notes = %s, processed_at = NOW()
            WHERE id = %s
        """, (notes, withdrawal_id))
        flash('Withdrawal approved.', 'success')
    elif action == 'reject':
        cur.execute("""
            UPDATE withdrawal_requests 
            SET status = 'rejected', admin_notes = %s, processed_at = NOW()
            WHERE id = %s
        """, (notes, withdrawal_id))
        flash('Withdrawal rejected.', 'warning')
    elif action == 'complete':
        cur.execute("""
            UPDATE withdrawal_requests 
            SET status = 'completed', admin_notes = %s, processed_at = NOW()
            WHERE id = %s
        """, (notes, withdrawal_id))
        flash('Withdrawal marked as completed.', 'success')
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('admin.admin_withdrawals'))

@admin_bp.route('/admin/analytics')
@login_required
@role_required(['admin'])
def admin_analytics():
    cur = get_db_connection()
    
    cur.execute("""
        SELECT DATE_FORMAT(booking_date, '%Y-%m') as month, COUNT(*) as count
        FROM bookings
        WHERE booking_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """)
    monthly_bookings = cur.fetchall()
    
    cur.execute("""
        SELECT DATE_FORMAT(booking_date, '%Y-%m') as month, SUM(platform_fee) as revenue
        FROM bookings
        WHERE status = 'completed' AND booking_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """)
    monthly_revenue = cur.fetchall()
    
    cur.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m') as month, 
               COUNT(*) as count,
               SUM(CASE WHEN user_type = 'parent' THEN 1 ELSE 0 END) as parents,
               SUM(CASE WHEN user_type = 'babysitter' THEN 1 ELSE 0 END) as babysitters
        FROM users
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY month
        ORDER BY month
    """)
    user_growth = cur.fetchall()
    
    cur.execute("""
        SELECT u.full_name, bp.total_bookings, bp.rating_average, bp.total_earnings
        FROM babysitter_profiles bp
        JOIN users u ON bp.user_id = u.id
        ORDER BY bp.total_bookings DESC
        LIMIT 10
    """)
    top_babysitters = cur.fetchall()
    
    cur.close()
    
    return render_template('admin/analytics.html',
                         monthly_bookings=monthly_bookings,
                         monthly_revenue=monthly_revenue,
                         user_growth=user_growth,
                         top_babysitters=top_babysitters)

@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def admin_settings():
    cur = get_db_connection()
    
    if request.method == 'POST':
        allowed_settings = ['platform_fee_percent', 'minimum_withdrawal', 'support_email', 'contact_phone']
        
        for key in request.form:
            if key in allowed_settings:
                cur.execute("""
                    UPDATE settings SET setting_value = %s WHERE setting_key = %s
                """, (request.form.get(key), key))
        
        mysql.connection.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin.admin_settings'))
    
    cur.execute("SELECT * FROM settings")
    settings = cur.fetchall()
    cur.close()
    
    return render_template('admin/settings.html', settings=settings)

@admin_bp.route('/admin/logs')
@login_required
@role_required(['admin'])
def admin_logs():
    cur = get_db_connection()
    
    cur.execute("""
        SELECT al.*, u.full_name as admin_name
        FROM admin_logs al
        JOIN users u ON al.admin_id = u.id
        ORDER BY al.created_at DESC
        LIMIT 100
    """)
    logs = cur.fetchall()
    cur.close()
    
    return render_template('admin/logs.html', logs=logs)

#API ROUTES

@admin_bp.route('/api/notifications/unread')
@login_required
def api_unread_notifications():
    cur = get_db_connection()
    cur.execute("""
        SELECT COUNT(*) as count FROM notifications
        WHERE user_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    count = cur.fetchone()['count']
    cur.close()
    
    return jsonify({'unread_count': count})

@admin_bp.route('/api/messages/unread')
@login_required
def api_unread_messages():
    cur = get_db_connection()
    cur.execute("""
        SELECT COUNT(*) as count FROM messages
        WHERE receiver_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    count = cur.fetchone()['count']
    cur.close()
    
    return jsonify({'unread_count': count})

@admin_bp.route('/admin/secure-file/<filename>')
@login_required
@role_required(['admin'])
def admin_secure_file(filename):
    return send_from_directory(current_app.config['SECURE_UPLOAD_FOLDER'], filename)

