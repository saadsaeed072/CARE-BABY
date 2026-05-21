from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from extensions import mysql, socketio
from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required

parent_bp = Blueprint('parent', __name__)

#PARENT ROUTES

@parent_bp.route('/parent/dashboard')
@login_required
@role_required(['parent'])
def parent_dashboard():
    cur = get_db_connection()
    
    cur.execute("""
        SELECT b.*, u.id as sitter_id, u.full_name as sitter_name, u.phone as sitter_phone, u.profile_image as sitter_image
        FROM bookings b
        JOIN babysitter_profiles bp ON b.babysitter_id = bp.id
        JOIN users u ON bp.user_id = u.id
       WHERE b.parent_id = %s AND b.booking_date >= CURDATE()
    AND b.status IN ('confirmed', 'pending', 'in_progress')
    ORDER BY b.booking_date, b.start_time
    """, (session['user_id'],))
    upcoming_bookings = cur.fetchall()
    
    for booking in upcoming_bookings:
        booking['formatted_start'] = (datetime.min + booking['start_time']).time().strftime('%I:%M %p')
        booking['formatted_end'] = (datetime.min + booking['end_time']).time().strftime('%I:%M %p')
    
    cur.execute("""
        SELECT b.*, u.id as sitter_id, u.full_name as sitter_name, u.profile_image as sitter_image
        FROM bookings b
        JOIN babysitter_profiles bp ON b.babysitter_id = bp.id
        JOIN users u ON bp.user_id = u.id
        WHERE b.parent_id = %s AND (b.status = 'completed' OR b.booking_date < CURDATE())
        ORDER BY b.booking_date DESC
        LIMIT 5
    """, (session['user_id'],))
    booking_history = cur.fetchall()
    
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
    
    return render_template('parent/dashboard.html',
                         upcoming_bookings=upcoming_bookings,
                         booking_history=booking_history,
                         unread_messages=unread_messages,
                         unread_notifications=unread_notifications)

@parent_bp.route('/parent/profile', methods=['GET', 'POST'])
@login_required
@role_required(['parent'])
def parent_profile():
    cur = get_db_connection()
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        family_name = request.form.get('family_name', '').strip()
        number_of_children = request.form.get('number_of_children')
        children_ages = request.form.get('children_ages', '').strip()
        special_needs = request.form.get('special_needs', '').strip()
        emergency_contact_name = request.form.get('emergency_contact_name', '').strip()
        emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
        
        # Validate required fields
        if not full_name or not phone or not city:
            flash('Full name, phone, and city are required.', 'danger')
            return redirect(url_for('parent.parent_profile'))
        
        # Validate number_of_children as integer
        if number_of_children:
            try:
                number_of_children = int(number_of_children)
                if number_of_children < 0:
                    number_of_children = 0
            except (ValueError, TypeError):
                number_of_children = 0
        
        cur.execute("""
            UPDATE users SET full_name = %s, phone = %s, city = %s, address = %s
            WHERE id = %s
        """, (full_name, phone, city, address, session['user_id']))
        
        cur.execute("""
            UPDATE parent_profiles 
            SET family_name = %s, number_of_children = %s, children_ages = %s,
                special_needs = %s, emergency_contact_name = %s, emergency_contact_phone = %s
            WHERE user_id = %s
        """, (family_name, number_of_children, children_ages, special_needs,
              emergency_contact_name, emergency_contact_phone, session['user_id']))
        
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
        
        return redirect(url_for('parent.parent_profile'))
    
    cur.execute("""
        SELECT u.*, pp.*
        FROM users u
        LEFT JOIN parent_profiles pp ON u.id = pp.user_id
        WHERE u.id = %s
    """, (session['user_id'],))
    user = cur.fetchone()
    cur.close()
    
    return render_template('parent/profile.html', user=user)

@parent_bp.route('/parent/book/<int:sitter_id>', methods=['GET', 'POST'])
@login_required
@role_required(['parent'])
def book_babysitter(sitter_id):
    cur = get_db_connection()
    
    cur.execute("""
        SELECT u.id, u.full_name, u.city, u.profile_image,
               bp.id as profile_id, bp.hourly_rate, bp.years_of_experience
        FROM users u
        JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE u.id = %s AND u.user_type = 'babysitter'
    """, (sitter_id,))
    sitter = cur.fetchone()
    
    if not sitter:
        flash('Babysitter not found.', 'danger')
        return redirect(url_for('public.search'))
    
    if request.method == 'POST':
        booking_date = request.form.get('booking_date', '').strip()
        start_time = request.form.get('start_time', '').strip()
        end_time = request.form.get('end_time', '').strip()
        number_of_children = request.form.get('number_of_children', 1)
        children_ages = request.form.get('children_ages')
        special_instructions = request.form.get('special_instructions')
        
        # Validate required fields
        if not booking_date or not start_time or not end_time:
            flash('Please fill in date, start time, and end time.', 'danger')
            return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
        
        # Validate date format and not in the past
        try:
            booking_dt = datetime.strptime(booking_date, '%Y-%m-%d').date()
            if booking_dt < datetime.now().date():
                flash('Booking date cannot be in the past.', 'danger')
                return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
        
        # Validate time format and calculate hours
        try:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
        except ValueError:
            flash('Invalid time format.', 'danger')
            return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
        
        total_hours = (end - start).seconds / 3600
        
        if total_hours <= 0:
            flash('End time must be after start time.', 'danger')
            return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
            
        # Enforce babysitter availability
        db_day_of_week = (booking_dt.weekday() + 1) % 7
        start_td = timedelta(hours=start.hour, minutes=start.minute)
        end_td = timedelta(hours=end.hour, minutes=end.minute)
        
        cur.execute("""
            SELECT * FROM availability
            WHERE babysitter_id = %s AND day_of_week = %s AND is_available = TRUE
        """, (sitter['profile_id'], db_day_of_week))
        day_slots = cur.fetchall()
        
        is_available = False
        for slot in day_slots:
            if slot['start_time'] <= start_td and slot['end_time'] >= end_td:
                is_available = True
                break
                
        if not is_available:
            flash('The babysitter is not available for the requested time slot.', 'danger')
            return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
            
        # Check for overlapping existing bookings
        cur.execute("""
            SELECT id FROM bookings
            WHERE babysitter_id = %s AND booking_date = %s
            AND status NOT IN ('cancelled', 'rejected')
            AND start_time < %s AND end_time > %s
        """, (sitter['profile_id'], booking_date, end_time, start_time))
        
        if cur.fetchone():
            flash('The babysitter is already booked during this time slot.', 'danger')
            return redirect(url_for('parent.book_babysitter', sitter_id=sitter_id))
        
        # Validate number_of_children
        try:
            number_of_children = int(number_of_children)
            if number_of_children < 1:
                number_of_children = 1
        except (ValueError, TypeError):
            number_of_children = 1
        
        hourly_rate = float(sitter['hourly_rate'])
        
        total_amount = total_hours * hourly_rate
        platform_fee = total_amount * 0.10  # 10% platform fee
        babysitter_earnings = total_amount - platform_fee

        cur.execute("""
            INSERT INTO bookings (parent_id, babysitter_id, booking_date, start_time, end_time,
                                number_of_children, children_ages, special_instructions,
                                total_hours, hourly_rate, total_amount, platform_fee, babysitter_earnings)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['user_id'], sitter['profile_id'], booking_date, start_time, end_time,
              number_of_children, children_ages, special_instructions,
              total_hours, hourly_rate, total_amount, platform_fee, babysitter_earnings))
        
        booking_id = cur.lastrowid
        
        cur.execute("""
            INSERT INTO notifications (user_id, title, message, type, reference_id)
            VALUES (%s, %s, %s, 'booking', %s)
        """, (sitter['id'], 'New Booking Request', 
              f'You have a new booking request from {session["user_name"]}', booking_id))
        
        # Emit real-time notification
        socketio.emit('new_notification', {
            'title': 'New Booking Request',
            'message': f'You have a new booking request from {session["user_name"]}',
            'type': 'booking'
        }, to=f"user_{sitter['id']}")
        
        mysql.connection.commit()
        cur.close()
        
        flash('Booking request sent successfully!', 'success')
        return redirect(url_for('parent.parent_bookings'))
    
    cur.execute("""
        SELECT * FROM availability
        WHERE babysitter_id = %s AND is_available = TRUE
        ORDER BY day_of_week, start_time
    """, (sitter['profile_id'],))
    availability = cur.fetchall()
    
    for slot in availability:
        slot['formatted_start'] = (datetime.min + slot['start_time']).time().strftime('%I:%M %p')
        slot['formatted_end'] = (datetime.min + slot['end_time']).time().strftime('%I:%M %p')
    
    cur.close()
    
    return render_template('parent/book.html', sitter=sitter, availability=availability)

@parent_bp.route('/parent/bookings')
@login_required
@role_required(['parent'])
def parent_bookings():
    cur = get_db_connection()
    
    status_filter = request.args.get('status', 'all')
    
    query = """
        SELECT b.*, u.id as sitter_id, u.full_name as sitter_name, u.phone as sitter_phone, u.profile_image as sitter_image
        FROM bookings b
        JOIN babysitter_profiles bp ON b.babysitter_id = bp.id
        JOIN users u ON bp.user_id = u.id
        WHERE b.parent_id = %s
    """
    params = [session['user_id']]
    
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
    
    return render_template('parent/bookings.html', bookings=bookings, status_filter=status_filter)

@parent_bp.route('/parent/booking/<int:booking_id>/cancel', methods=['POST'])
@login_required
@role_required(['parent'])
def cancel_booking(booking_id):
    reason = request.form.get('cancellation_reason')
    
    cur = get_db_connection()
    
    cur.execute("SELECT * FROM bookings WHERE id = %s AND parent_id = %s", 
                (booking_id, session['user_id']))
    booking = cur.fetchone()
    
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('parent.parent_bookings'))
    
    if booking['status'] in ['completed', 'cancelled']:
        flash('Cannot cancel this booking.', 'danger')
        return redirect(url_for('parent.parent_bookings'))
    
    cur.execute("""
        UPDATE bookings 
        SET status = 'cancelled', cancelled_by = 'parent', cancellation_reason = %s
        WHERE id = %s
    """, (reason, booking_id))
    
    cur.execute("""
        INSERT INTO notifications (user_id, title, message, type, reference_id)
        SELECT u.id, 'Booking Cancelled', %s, 'booking', %s
        FROM babysitter_profiles bp
        JOIN users u ON bp.user_id = u.id
        WHERE bp.id = %s
    """, (f'Booking for {booking["booking_date"]} has been cancelled by parent', 
          booking_id, booking['babysitter_id']))

    # Get babysitter user id for socket emission
    cur.execute("SELECT user_id FROM babysitter_profiles WHERE id = %s", (booking['babysitter_id'],))
    sitter_user_id = cur.fetchone()['user_id']
    
    socketio.emit('new_notification', {
        'title': 'Booking Cancelled',
        'message': f'Booking for {booking["booking_date"]} has been cancelled by parent',
        'type': 'booking'
    }, to=f"user_{sitter_user_id}")
    
    mysql.connection.commit()
    cur.close()
    
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('parent.parent_bookings'))

@parent_bp.route('/parent/booking/<int:booking_id>/track')
@login_required
@role_required(['parent'])
def parent_track(booking_id):
    cur = get_db_connection()
    cur.execute("""
        SELECT b.*, u.full_name as sitter_name, u.phone as sitter_phone
        FROM bookings b
        JOIN babysitter_profiles bp ON b.babysitter_id = bp.id
        JOIN users u ON bp.user_id = u.id
        WHERE b.id = %s AND b.parent_id = %s AND b.status = 'in_progress'
    """, (booking_id, session['user_id']))
    booking = cur.fetchone()
    cur.close()
    
    if not booking:
        flash('Booking not found or not currently in progress.', 'warning')
        return redirect(url_for('parent.parent_bookings'))
        
    return render_template('parent/track.html', booking=booking)

@parent_bp.route('/parent/booking/<int:booking_id>/review', methods=['GET', 'POST'])
@login_required
@role_required(['parent'])
def leave_review(booking_id):
    cur = get_db_connection()
    
    cur.execute("""
        SELECT b.*, bp.user_id as sitter_user_id
        FROM bookings b
        JOIN babysitter_profiles bp ON b.babysitter_id = bp.id
        WHERE b.id = %s AND b.parent_id = %s AND b.status = 'completed'
    """, (booking_id, session['user_id']))
    booking = cur.fetchone()
    
    if not booking:
        flash('Booking not found or not eligible for review.', 'danger')
        return redirect(url_for('parent.parent_bookings'))
    
    cur.execute("SELECT id FROM reviews WHERE booking_id = %s", (booking_id,))
    if cur.fetchone():
        flash('You have already reviewed this booking.', 'warning')
        return redirect(url_for('parent.parent_bookings'))
    
    if request.method == 'POST':
        rating = request.form.get('rating')
        review_text = request.form.get('review_text', '').strip()
        
        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                flash('Rating must be between 1 and 5.', 'danger')
                return render_template('parent/review.html', booking=booking)
        except (ValueError, TypeError):
            flash('Please provide a valid rating.', 'danger')
            return render_template('parent/review.html', booking=booking)
        
        # Validate review text
        if not review_text:
            flash('Please write a review.', 'danger')
            return render_template('parent/review.html', booking=booking)
        
        cur.execute("""
            INSERT INTO reviews (booking_id, parent_id, babysitter_id, rating, review_text)
            VALUES (%s, %s, %s, %s, %s)
        """, (booking_id, session['user_id'], booking['babysitter_id'], rating, review_text))
        
        cur.execute("""
            UPDATE babysitter_profiles
            SET rating_average = (SELECT AVG(rating) FROM reviews WHERE babysitter_id = %s),
                rating_count = (SELECT COUNT(*) FROM reviews WHERE babysitter_id = %s)
            WHERE id = %s
        """, (booking['babysitter_id'], booking['babysitter_id'], booking['babysitter_id']))
        
        cur.execute("""
            INSERT INTO notifications (user_id, title, message, type, reference_id)
            VALUES (%s, %s, %s, 'booking', %s)
        """, (booking['sitter_user_id'], 'New Review Received',
              f'You received a {rating}-star review!', booking_id))
        
        socketio.emit('new_notification', {
            'title': 'New Review Received',
            'message': f'You received a {rating}-star review!',
            'type': 'booking'
        }, to=f"user_{booking['sitter_user_id']}")
        
        mysql.connection.commit()
        cur.close()
        
        flash('Review submitted successfully!', 'success')
        return redirect(url_for('parent.parent_bookings'))
    
    cur.close()
    return render_template('parent/review.html', booking=booking)

@parent_bp.route('/parent/messages')
@login_required
@role_required(['parent'])
def parent_messages():
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
    
    return render_template('parent/messages.html', conversations=conversations)

@parent_bp.route('/parent/messages/<int:user_id>')
@login_required
@role_required(['parent'])
def parent_chat(user_id):
    cur = get_db_connection()
    
    cur.execute("SELECT id, full_name, profile_image FROM users WHERE id = %s", (user_id,))
    other_user = cur.fetchone()
    
    if not other_user:
        flash('User not found.', 'danger')
        return redirect(url_for('parent.parent_messages'))
    
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
    
    return render_template('parent/chat.html', other_user=other_user, messages=messages)

@parent_bp.route('/parent/messages/send', methods=['POST'])
@login_required
@role_required(['parent'])
def send_message():
    receiver_id = request.form.get('receiver_id')
    message_text = request.form.get('message_text')
    booking_id = request.form.get('booking_id')
    
    if not receiver_id or not message_text:
        flash('Invalid message.', 'danger')
        return redirect(url_for('parent.parent_messages'))
    
    cur = get_db_connection()
    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, booking_id, message_text)
        VALUES (%s, %s, %s, %s)
    """, (session['user_id'], receiver_id, booking_id if booking_id else None, message_text))
    
    socketio.emit('new_message', {
        'sender_id': session['user_id'],
        'sender_name': session['user_name'],
        'message_text': message_text
    }, to=f"user_{receiver_id}")
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('parent.parent_chat', user_id=receiver_id))

@parent_bp.route('/parent/notifications')
@login_required
@role_required(['parent'])
def parent_notifications():
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
    
    return render_template('parent/notifications.html', notifications=notifications)

