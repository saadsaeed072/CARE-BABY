from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from extensions import mysql, socketio
from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required

babysitter_bp = Blueprint('babysitter', __name__)

#BABYSITTER ROUTES

@babysitter_bp.route('/babysitter/dashboard')
@login_required
@role_required(['babysitter'])
def babysitter_dashboard():
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    
    if not profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('auth.logout'))
    
    babysitter_id = profile['id']
    
    cur.execute("""
        SELECT b.*, u.full_name as parent_name, u.phone as parent_phone, u.profile_image as parent_image
        FROM bookings b
        JOIN users u ON b.parent_id = u.id
        WHERE b.babysitter_id = %s AND b.status = 'pending'
        ORDER BY b.created_at DESC
    """, (babysitter_id,))
    pending_requests = cur.fetchall()
    
    cur.execute("""
        SELECT b.*, u.full_name as parent_name, u.phone as parent_phone, u.profile_image as parent_image
        FROM bookings b
        JOIN users u ON b.parent_id = u.id
        WHERE b.babysitter_id = %s AND b.booking_date >= CURDATE()
        AND b.status IN ('confirmed', 'in_progress')
        ORDER BY b.booking_date, b.start_time
    """, (babysitter_id,))
    upcoming_bookings = cur.fetchall()
    
    for req in pending_requests:
        req['formatted_start'] = (datetime.min + req['start_time']).time().strftime('%I:%M %p')
        req['formatted_end'] = (datetime.min + req['end_time']).time().strftime('%I:%M %p')
        
    for booking in upcoming_bookings:
        booking['formatted_start'] = (datetime.min + booking['start_time']).time().strftime('%I:%M %p')
        booking['formatted_end'] = (datetime.min + booking['end_time']).time().strftime('%I:%M %p')
    
    cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'completed' THEN babysitter_earnings ELSE 0 END), 0) as total_earnings,
            COALESCE(SUM(CASE WHEN status = 'completed' AND booking_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN babysitter_earnings ELSE 0 END), 0) as monthly_earnings,
            COALESCE(SUM(CASE WHEN status = 'confirmed' THEN babysitter_earnings ELSE 0 END), 0) as pending_earnings
        FROM bookings
        WHERE babysitter_id = %s
    """, (babysitter_id,))
    earnings = cur.fetchone()
    
    cur.execute("""
        SELECT COUNT(*) as count FROM messages
        WHERE receiver_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    unread_messages = cur.fetchone()['count']
    
    cur.execute("""
        SELECT COUNT(*) as count FROM notifications
        WHERE user_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    unread_notifications = cur.fetchone()['count']
    
    cur.close()
    
    return render_template('babysitter/dashboard.html',
                         pending_requests=pending_requests,
                         upcoming_bookings=upcoming_bookings,
                         earnings=earnings,
                         unread_messages=unread_messages,
                         unread_notifications=unread_notifications)

@babysitter_bp.route('/babysitter/profile', methods=['GET', 'POST'])
@login_required
@role_required(['babysitter'])
def babysitter_profile_edit():
    cur = get_db_connection()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        date_of_birth = request.form.get('date_of_birth')
        gender = request.form.get('gender')
        hourly_rate = request.form.get('hourly_rate')
        years_of_experience = request.form.get('years_of_experience')
        about_me = request.form.get('about_me')
        education = request.form.get('education')
        languages = request.form.get('languages')
        special_skills = request.form.get('special_skills')
        certifications = request.form.get('certifications')
        has_cpr = 'has_cpr' in request.form
        has_first_aid = 'has_first_aid' in request.form
        
        # Validate required fields
        if not full_name or not phone or not city:
            flash('Full name, phone, and city are required.', 'danger')
            return redirect(url_for('babysitter.babysitter_profile_edit'))
        
        # Validate hourly_rate range
        if hourly_rate:
            try:
                hourly_rate = float(hourly_rate)
                if hourly_rate < 300 or hourly_rate > 2000:
                    flash('Hourly rate must be between Rs. 300 and Rs. 2,000.', 'danger')
                    return redirect(url_for('babysitter.babysitter_profile_edit'))
            except (ValueError, TypeError):
                flash('Please enter a valid hourly rate.', 'danger')
                return redirect(url_for('babysitter.babysitter_profile_edit'))
        
        # Validate years_of_experience
        if years_of_experience:
            try:
                years_of_experience = int(years_of_experience)
                if years_of_experience < 0:
                    years_of_experience = 0
            except (ValueError, TypeError):
                years_of_experience = 0
        
        # Validate gender
        if gender and gender not in ['male', 'female', 'other']:
            flash('Invalid gender selection.', 'danger')
            return redirect(url_for('babysitter.babysitter_profile_edit'))
        
        cur.execute("""
            UPDATE users SET full_name = %s, phone = %s, city = %s, address = %s
            WHERE id = %s
        """, (full_name, phone, city, address, session['user_id']))
        
        cur.execute("""
            UPDATE babysitter_profiles 
            SET date_of_birth = %s, gender = %s, hourly_rate = %s, years_of_experience = %s,
                about_me = %s, education = %s, languages = %s, special_skills = %s,
                certifications = %s, has_cpr = %s, has_first_aid = %s
            WHERE user_id = %s
        """, (date_of_birth, gender, hourly_rate, years_of_experience,
              about_me, education, languages, special_skills,
              certifications, has_cpr, has_first_aid, session['user_id']))
        
        mysql.connection.commit()
        flash('Profile updated successfully!', 'success')
        
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file and allowed_file(file.filename):
                filename = f"user_{session['user_id']}_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                cur.execute("UPDATE users SET profile_image = %s WHERE id = %s",
                          (filename, session['user_id']))
                mysql.connection.commit()
        
        return redirect(url_for('babysitter.babysitter_profile_edit'))
    
    cur.execute("""
        SELECT u.*, bp.*
        FROM users u
        LEFT JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE u.id = %s
    """, (session['user_id'],))
    user = cur.fetchone()
    cur.close()
    
    return render_template('babysitter/profile.html', user=user)

@babysitter_bp.route('/babysitter/verification', methods=['GET', 'POST'])
@login_required
@role_required(['babysitter'])
def babysitter_verification():
    cur = get_db_connection()
    
    if request.method == 'POST':
        cnic_number = request.form.get('cnic_number', '').strip()
        
        # Validate CNIC format (XXXXX-XXXXXXX-X)
        if not cnic_number:
            flash('Please enter your CNIC number.', 'danger')
            return redirect(url_for('babysitter.babysitter_verification'))
        
        cnic_cleaned = cnic_number.replace('-', '')
        if not cnic_cleaned.isdigit() or len(cnic_cleaned) != 13:
            flash('Please enter a valid CNIC number (e.g. 12345-1234567-1).', 'danger')
            return redirect(url_for('babysitter.babysitter_verification'))
        
        cnic_front = None
        if 'cnic_front' in request.files:
            file = request.files['cnic_front']
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash('Invalid file type for CNIC front. Only PDF, PNG, JPEG are allowed.', 'danger')
                    return redirect(url_for('babysitter.babysitter_verification'))
                cnic_front = f"cnic_front_{session['user_id']}_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cnic_front))
        
        cnic_back = None
        if 'cnic_back' in request.files:
            file = request.files['cnic_back']
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash('Invalid file type for CNIC back. Only PDF, PNG, JPEG are allowed.', 'danger')
                    return redirect(url_for('babysitter.babysitter_verification'))
                cnic_back = f"cnic_back_{session['user_id']}_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cnic_back))
        
        update_fields = ["cnic_number = %s", "verification_status = 'pending'"]
        params = [cnic_number]
        
        if cnic_front:
            update_fields.append("cnic_front_image = %s")
            params.append(cnic_front)
        
        if cnic_back:
            update_fields.append("cnic_back_image = %s")
            params.append(cnic_back)
        
        params.append(session['user_id'])
        
        cur.execute(f"""
            UPDATE babysitter_profiles 
            SET {', '.join(update_fields)}
            WHERE user_id = %s
        """, params)
        
        mysql.connection.commit()
        flash('Verification documents submitted successfully!', 'success')
        return redirect(url_for('babysitter.babysitter_verification'))
    
    cur.execute("""
        SELECT cnic_number, cnic_front_image, cnic_back_image, 
               verification_status, background_check_status
        FROM babysitter_profiles
        WHERE user_id = %s
    """, (session['user_id'],))
    verification = cur.fetchone()
    cur.close()
    
    return render_template('babysitter/verification.html', verification=verification)

@babysitter_bp.route('/babysitter/availability', methods=['GET', 'POST'])
@login_required
@role_required(['babysitter'])
def babysitter_availability():
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    babysitter_id = profile['id']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            day_of_week = request.form.get('day_of_week', '').strip()
            start_time = request.form.get('start_time', '').strip()
            end_time = request.form.get('end_time', '').strip()
            
            # Validate required fields
            if not day_of_week or not start_time or not end_time:
                flash('Please fill in all availability fields.', 'danger')
                return redirect(url_for('babysitter.babysitter_availability'))
            
            # Validate day_of_week range
            try:
                day_of_week = int(day_of_week)
                if day_of_week < 0 or day_of_week > 6:
                    flash('Invalid day of week.', 'danger')
                    return redirect(url_for('babysitter.babysitter_availability'))
            except (ValueError, TypeError):
                flash('Invalid day of week.', 'danger')
                return redirect(url_for('babysitter.babysitter_availability'))
            
            # Validate end_time > start_time
            try:
                st = datetime.strptime(start_time, '%H:%M')
                et = datetime.strptime(end_time, '%H:%M')
                if et <= st:
                    flash('End time must be after start time.', 'danger')
                    return redirect(url_for('babysitter.babysitter_availability'))
            except ValueError:
                flash('Invalid time format.', 'danger')
                return redirect(url_for('babysitter.babysitter_availability'))
            
            try:
                cur.execute("""
                    INSERT INTO availability (babysitter_id, day_of_week, start_time, end_time)
                    VALUES (%s, %s, %s, %s)
                """, (babysitter_id, day_of_week, start_time, end_time))
                mysql.connection.commit()
                flash('Availability added successfully!', 'success')
            except Exception as e:
                flash('This time slot already exists.', 'warning')
        
        elif action == 'delete':
            availability_id = request.form.get('availability_id')
            cur.execute("DELETE FROM availability WHERE id = %s AND babysitter_id = %s",
                       (availability_id, babysitter_id))
            mysql.connection.commit()
            flash('Availability removed.', 'success')
        
        return redirect(url_for('babysitter.babysitter_availability'))
    
    cur.execute("""
        SELECT * FROM availability
        WHERE babysitter_id = %s
        ORDER BY day_of_week, start_time
    """, (babysitter_id,))
    availability = cur.fetchall()
    
    for slot in availability:
        slot['formatted_start'] = (datetime.min + slot['start_time']).time().strftime('%I:%M %p')
        slot['formatted_end'] = (datetime.min + slot['end_time']).time().strftime('%I:%M %p')
    
    cur.execute("""
        SELECT * FROM blocked_dates
        WHERE babysitter_id = %s AND blocked_date >= CURDATE()
        ORDER BY blocked_date
    """, (babysitter_id,))
    blocked_dates = cur.fetchall()
    
    cur.close()
    
    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    return render_template('babysitter/availability.html', 
                         availability=availability, 
                         blocked_dates=blocked_dates,
                         days=days)

@babysitter_bp.route('/babysitter/bookings')
@login_required
@role_required(['babysitter'])
def babysitter_bookings():
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    babysitter_id = profile['id']
    
    status_filter = request.args.get('status', 'all')
    
    query = """
        SELECT b.*, u.full_name as parent_name, u.phone as parent_phone, u.profile_image as parent_image
        FROM bookings b
        JOIN users u ON b.parent_id = u.id
        WHERE b.babysitter_id = %s
    """
    params = [babysitter_id]
    
    if status_filter != 'all':
        query += " AND b.status = %s"
        params.append(status_filter)
    
    query += " ORDER BY b.booking_date DESC, b.start_time DESC"
    
    cur.execute(query, params)
    bookings = cur.fetchall()
    
    for booking in bookings:
        booking['formatted_start'] = (datetime.min + booking['start_time']).time().strftime('%I:%M %p')
        booking['formatted_end'] = (datetime.min + booking['end_time']).time().strftime('%I:%M %p')
    
    cur.close()
    
    return render_template('babysitter/bookings.html', bookings=bookings, status_filter=status_filter)

@babysitter_bp.route('/babysitter/booking/<int:booking_id>/<action>')
@login_required
@role_required(['babysitter'])
def update_booking_status(booking_id, action):
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    babysitter_id = profile['id']
    
    cur.execute("SELECT * FROM bookings WHERE id = %s AND babysitter_id = %s", 
                (booking_id, babysitter_id))
    booking = cur.fetchone()
    
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('babysitter.babysitter_bookings'))
    
    if action == 'accept':
        cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
        message = 'Booking accepted successfully!'
    elif action == 'reject':
        cur.execute("UPDATE bookings SET status = 'rejected' WHERE id = %s", (booking_id,))
        message = 'Booking rejected.'
    elif action == 'complete':
        booking_end = datetime.combine(booking['booking_date'], (datetime.min + booking['end_time']).time())
        if datetime.now() < booking_end:
            flash('You cannot complete this booking until the job time has ended.', 'warning')
            return redirect(url_for('babysitter.babysitter_bookings'))
            
        cur.execute("UPDATE bookings SET status = 'completed' WHERE id = %s", (booking_id,))
        
        cur.execute("""
            UPDATE babysitter_profiles
            SET total_bookings = total_bookings + 1,
                total_earnings = total_earnings + %s
            WHERE id = %s
        """, (booking['babysitter_earnings'], babysitter_id))
        
        message = 'Booking marked as completed!'
    else:
        flash('Invalid action.', 'danger')
        return redirect(url_for('babysitter.babysitter_bookings'))
    
    cur.execute("""
        INSERT INTO notifications (user_id, title, message, type, reference_id)
        VALUES (%s, %s, %s, 'booking', %s)
    """, (booking['parent_id'], f'Booking {action.title()}ed', 
          f'Your booking has been {action}ed by the babysitter', booking_id))
    
    socketio.emit('new_notification', {
        'title': f'Booking {action.title()}ed',
        'message': f'Your booking has been {action}ed by the babysitter',
        'type': 'booking'
    }, room=f"user_{booking['parent_id']}")
    
    mysql.connection.commit()
    cur.close()
    
    flash(message, 'success')
    return redirect(url_for('babysitter.babysitter_bookings'))

@babysitter_bp.route('/babysitter/earnings')
@login_required
@role_required(['babysitter'])
def babysitter_earnings():
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    babysitter_id = profile['id']
    
    cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'completed' THEN babysitter_earnings ELSE 0 END), 0) as total_earnings,
            COALESCE(SUM(CASE WHEN status = 'completed' AND booking_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) THEN babysitter_earnings ELSE 0 END), 0) as monthly_earnings,
            COALESCE(SUM(CASE WHEN status = 'completed' AND booking_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN babysitter_earnings ELSE 0 END), 0) as weekly_earnings,
            COALESCE(SUM(CASE WHEN status = 'confirmed' THEN babysitter_earnings ELSE 0 END), 0) as pending_earnings
        FROM bookings
        WHERE babysitter_id = %s
    """, (babysitter_id,))
    summary = cur.fetchone()
    
    cur.execute("""
        SELECT b.*, u.full_name as parent_name
        FROM bookings b
        JOIN users u ON b.parent_id = u.id
        WHERE b.babysitter_id = %s AND b.status = 'completed'
        ORDER BY b.booking_date DESC
        LIMIT 10
    """, (babysitter_id,))
    recent_earnings = cur.fetchall()
    
    cur.execute("""
        SELECT * FROM withdrawal_requests
        WHERE babysitter_id = %s
        ORDER BY requested_at DESC
    """, (babysitter_id,))
    withdrawals = cur.fetchall()
    
    cur.close()
    
    return render_template('babysitter/earnings.html',
                         summary=summary,
                         recent_earnings=recent_earnings,
                         withdrawals=withdrawals)

@babysitter_bp.route('/babysitter/withdraw', methods=['POST'])
@login_required
@role_required(['babysitter'])
def request_withdrawal():
    try:
        amount = float(request.form.get('amount', 0))
    except (ValueError, TypeError):
        flash('Please enter a valid amount.', 'danger')
        return redirect(url_for('babysitter.babysitter_earnings'))
    
    payment_method = request.form.get('payment_method')
    
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    babysitter_id = profile['id']
    
    if amount < 1000:
        flash('Minimum withdrawal amount is Rs. 1,000.', 'warning')
        return redirect(url_for('babysitter.babysitter_earnings'))
    
    cur.execute("""
        SELECT COALESCE(SUM(babysitter_earnings), 0) as total_earnings
        FROM bookings
        WHERE babysitter_id = %s AND status = 'completed'
    """, (babysitter_id,))
    total_earnings = cur.fetchone()['total_earnings']
    
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) as total_withdrawn
        FROM withdrawal_requests
        WHERE babysitter_id = %s AND status IN ('pending', 'approved', 'completed')
    """, (babysitter_id,))
    total_withdrawn = cur.fetchone()['total_withdrawn']
    
    available_balance = total_earnings - total_withdrawn
    
    if amount > available_balance:
        flash('Insufficient balance for withdrawal.', 'danger')
        return redirect(url_for('babysitter.babysitter_earnings'))
    
    bank_name = request.form.get('bank_name')
    account_number = request.form.get('account_number')
    account_title = request.form.get('account_title')
    easypaisa_number = request.form.get('easypaisa_number')
    jazzcash_number = request.form.get('jazzcash_number')
    
    cur.execute("""
        INSERT INTO withdrawal_requests 
        (babysitter_id, amount, bank_name, account_number, account_title, 
         easypaisa_number, jazzcash_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (babysitter_id, amount, bank_name, account_number, account_title,
          easypaisa_number, jazzcash_number))
    
    mysql.connection.commit()
    cur.close()
    
    flash('Withdrawal request submitted successfully!', 'success')
    return redirect(url_for('babysitter.babysitter_earnings'))

@babysitter_bp.route('/babysitter/messages')
@login_required
@role_required(['babysitter'])
def babysitter_messages():
    cur = get_db_connection()
    
    cur.execute("""
        SELECT DISTINCT 
            CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END as other_user_id,
            u.full_name, u.profile_image,
            (SELECT message_text FROM messages 
             WHERE (sender_id = %s AND receiver_id = other_user_id) 
                OR (sender_id = other_user_id AND receiver_id = %s)
             ORDER BY created_at DESC LIMIT 1) as last_message,
            (SELECT created_at FROM messages 
             WHERE (sender_id = %s AND receiver_id = other_user_id) 
                OR (sender_id = other_user_id AND receiver_id = %s)
             ORDER BY created_at DESC LIMIT 1) as last_message_time,
            (SELECT COUNT(*) FROM messages WHERE sender_id = other_user_id AND receiver_id = %s AND is_read = FALSE) as unread_count
        FROM messages m
        JOIN users u ON (CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END) = u.id
        WHERE m.sender_id = %s OR m.receiver_id = %s
        ORDER BY last_message_time DESC
    """, (session['user_id'],) * 9)
    conversations = cur.fetchall()
    
    cur.close()
    
    return render_template('babysitter/messages.html', conversations=conversations)

@babysitter_bp.route('/babysitter/messages/<int:user_id>')
@login_required
@role_required(['babysitter'])
def babysitter_chat(user_id):
    cur = get_db_connection()
    
    cur.execute("SELECT id, full_name, profile_image FROM users WHERE id = %s", (user_id,))
    other_user = cur.fetchone()
    
    if not other_user:
        flash('User not found.', 'danger')
        return redirect(url_for('babysitter.babysitter_messages'))
    
    cur.execute("""
        SELECT m.*, 
               CASE WHEN m.sender_id = %s THEN 'sent' ELSE 'received' END as message_type
        FROM messages m
        WHERE (m.sender_id = %s AND m.receiver_id = %s)
           OR (m.sender_id = %s AND m.receiver_id = %s)
        ORDER BY m.created_at ASC
    """, (session['user_id'], session['user_id'], user_id, user_id, session['user_id']))
    messages = cur.fetchall()
    
    cur.execute("""
        UPDATE messages SET is_read = TRUE
        WHERE sender_id = %s AND receiver_id = %s AND is_read = FALSE
    """, (user_id, session['user_id']))
    
    mysql.connection.commit()
    cur.close()
    
    return render_template('babysitter/chat.html', other_user=other_user, messages=messages)

@babysitter_bp.route('/babysitter/messages/send', methods=['POST'])
@login_required
@role_required(['babysitter'])
def babysitter_send_message():
    receiver_id = request.form.get('receiver_id')
    message_text = request.form.get('message_text')
    booking_id = request.form.get('booking_id')
    
    if not receiver_id or not message_text:
        flash('Invalid message.', 'danger')
        return redirect(url_for('babysitter.babysitter_messages'))
    
    cur = get_db_connection()
    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, booking_id, message_text)
        VALUES (%s, %s, %s, %s)
    """, (session['user_id'], receiver_id, booking_id if booking_id else None, message_text))
    
    socketio.emit('new_message', {
        'sender_id': session['user_id'],
        'sender_name': session['user_name'],
        'message_text': message_text
    }, room=f"user_{receiver_id}")
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('babysitter.babysitter_chat', user_id=receiver_id))

@babysitter_bp.route('/babysitter/notifications')
@login_required
@role_required(['babysitter'])
def babysitter_notifications():
    cur = get_db_connection()
    
    cur.execute("""
        SELECT * FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 50
    """, (session['user_id'],))
    notifications = cur.fetchall()
    
    cur.execute("""
        UPDATE notifications SET is_read = TRUE
        WHERE user_id = %s AND is_read = FALSE
    """, (session['user_id'],))
    
    mysql.connection.commit()
    cur.close()
    
    return render_template('babysitter/notifications.html', notifications=notifications)

