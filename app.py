from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta    
import os
import secrets
import re

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'babycare_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

mysql = MySQL(app)

# Helper functions
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
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please login to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('user_type') not in allowed_roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_db_connection():
    return mysql.connection.cursor()

# Context processor for template variables
@app.context_processor
def inject_globals():
    return {
        'datetime': datetime, 
        'current_year': datetime.now().year,
        'app_name': 'BabyCare',
        'app_tagline': 'Trusted Childcare for Pakistani Families'
    }

#PUBLIC ROUTES 

@app.route('/')
def index():
    cur = get_db_connection()

    cur.execute("""
        SELECT u.id, u.full_name, u.city, u.profile_image,
               bp.hourly_rate, bp.years_of_experience, bp.rating_average, bp.rating_count,
               bp.languages, bp.special_skills
        FROM users u
        JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE u.user_type = 'babysitter' AND u.is_active = TRUE 
        AND bp.verification_status = 'verified'
        ORDER BY bp.rating_average DESC, bp.total_bookings DESC
        LIMIT 6
    """)
    featured_sitters = cur.fetchall()
    
    cur.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'parent' AND is_active = TRUE")
    parent_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM users WHERE user_type = 'babysitter' AND is_active = TRUE AND is_verified = TRUE")
    sitter_count = cur.fetchone()['count']
    
    cur.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'completed'")
    booking_count = cur.fetchone()['count']
    
    cur.close()
    
    return render_template('index.html', 
                         featured_sitters=featured_sitters,
                         parent_count=parent_count,
                         sitter_count=sitter_count,
                         booking_count=booking_count)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not name or not email or not subject or not message:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('contact'))
        
        # Validate email format
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('contact'))
        
        cur = get_db_connection()
        cur.execute("""
            INSERT INTO contact_messages (name, email, phone, subject, message)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, phone, subject, message))
        mysql.connection.commit()
        cur.close()
        
        flash('Your message has been sent successfully! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/help')
def help_center():
    return render_template('help.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/search')
def search():
    city = request.args.get('city', '')
    min_rate = request.args.get('min_rate', '')
    max_rate = request.args.get('max_rate', '')
    experience = request.args.get('experience', '')
    language = request.args.get('language', '')
    
    cur = get_db_connection()
    
    query = """
        SELECT u.id, u.full_name, u.city, u.profile_image,
               bp.hourly_rate, bp.years_of_experience, bp.rating_average, bp.rating_count,
               bp.languages, bp.special_skills, bp.about_me, bp.verification_status
        FROM users u
        JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE u.user_type = 'babysitter' AND u.is_active = TRUE
        AND bp.verification_status = 'verified'
    """
    params = []
    
    if city:
        query += " AND u.city LIKE %s"
        params.append(f'%{city}%')
    
    if min_rate:
        query += " AND bp.hourly_rate >= %s"
        params.append(min_rate)
    
    if max_rate:
        query += " AND bp.hourly_rate <= %s"
        params.append(max_rate)
    
    if experience:
        query += " AND bp.years_of_experience >= %s"
        params.append(experience)
    
    if language:
        query += " AND bp.languages LIKE %s"
        params.append(f'%{language}%')
    
    query += " ORDER BY bp.rating_average DESC, bp.total_bookings DESC"
    
    cur.execute(query, params)
    sitters = cur.fetchall()
    
    cur.execute("SELECT DISTINCT city FROM users WHERE user_type = 'babysitter' AND is_active = TRUE ORDER BY city")
    cities = cur.fetchall()
    
    cur.close()
    
    return render_template('search.html', 
                         sitters=sitters, 
                         cities=cities,
                         filters={
                             'city': city,
                             'min_rate': min_rate,
                             'max_rate': max_rate,
                             'experience': experience,
                             'language': language
                         })

@app.route('/babysitter/<int:id>')
def babysitter_profile(id):
    cur = get_db_connection()
    
    cur.execute("""
        SELECT u.*, bp.*
        FROM users u
        JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE u.id = %s AND u.user_type = 'babysitter'
    """, (id,))
    sitter = cur.fetchone()
    
    if not sitter:
        flash('Babysitter not found.', 'danger')
        return redirect(url_for('search'))
    
    cur.execute("""
        SELECT r.*, u.full_name as parent_name, u.profile_image as parent_image,
               b.booking_date
        FROM reviews r
        JOIN users u ON r.parent_id = u.id
        JOIN bookings b ON r.booking_id = b.id
        WHERE r.babysitter_id = %s AND r.is_visible = TRUE
        ORDER BY r.created_at DESC
    """, (sitter['id'],))
    reviews = cur.fetchall()
    
    cur.execute("""
        SELECT * FROM availability
        WHERE babysitter_id = %s AND is_available = TRUE
        ORDER BY day_of_week, start_time
    """, (sitter['id'],))
    availability = cur.fetchall()
    
    cur.close()
    
    return render_template('babysitter_profile.html', 
                         sitter=sitter, 
                         reviews=reviews,
                         availability=availability)

#AUTHENTICATION ROUTES

@app.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('register'))
        
        # Validate user_type (prevent admin injection)
        if user_type not in ['parent', 'babysitter']:
            flash('Invalid account type.', 'danger')
            return redirect(url_for('register'))
        
        # Validate email format
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('register'))
        
        # Validate phone format
        if not is_valid_phone(phone):
            flash('Please enter a valid phone number (e.g. 03001234567).', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('register'))
        
        cur = get_db_connection()
        
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'danger')
            cur.close()
            return redirect(url_for('register'))
        
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
        return redirect(url_for('login'))
    
    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
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
                return redirect(url_for('admin_dashboard'))
            elif user['user_type'] == 'babysitter':
                return redirect(url_for('babysitter_dashboard'))
            else:
                return redirect(url_for('parent_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

#PARENT ROUTES

@app.route('/parent/dashboard')
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

@app.route('/parent/profile', methods=['GET', 'POST'])
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
            return redirect(url_for('parent_profile'))
        
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
                filename = f"user_{session['user_id']}_{secure_filename(file.filename)}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                cur.execute("UPDATE users SET profile_image = %s WHERE id = %s",
                          (filename, session['user_id']))
                mysql.connection.commit()
        
        return redirect(url_for('parent_profile'))
    
    cur.execute("""
        SELECT u.*, pp.*
        FROM users u
        LEFT JOIN parent_profiles pp ON u.id = pp.user_id
        WHERE u.id = %s
    """, (session['user_id'],))
    user = cur.fetchone()
    cur.close()
    
    return render_template('parent/profile.html', user=user)

@app.route('/parent/book/<int:sitter_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('search'))
    
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
            return redirect(url_for('book_babysitter', sitter_id=sitter_id))
        
        # Validate date format and not in the past
        try:
            booking_dt = datetime.strptime(booking_date, '%Y-%m-%d').date()
            if booking_dt < datetime.now().date():
                flash('Booking date cannot be in the past.', 'danger')
                return redirect(url_for('book_babysitter', sitter_id=sitter_id))
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('book_babysitter', sitter_id=sitter_id))
        
        # Validate time format and calculate hours
        try:
            start = datetime.strptime(start_time, '%H:%M')
            end = datetime.strptime(end_time, '%H:%M')
        except ValueError:
            flash('Invalid time format.', 'danger')
            return redirect(url_for('book_babysitter', sitter_id=sitter_id))
        
        total_hours = (end - start).seconds / 3600
        
        if total_hours <= 0:
            flash('End time must be after start time.', 'danger')
            return redirect(url_for('book_babysitter', sitter_id=sitter_id))
        
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
        
        mysql.connection.commit()
        cur.close()
        
        flash('Booking request sent successfully!', 'success')
        return redirect(url_for('parent_bookings'))
    
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

@app.route('/parent/bookings')
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

@app.route('/parent/booking/<int:booking_id>/cancel', methods=['POST'])
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
        return redirect(url_for('parent_bookings'))
    
    if booking['status'] in ['completed', 'cancelled']:
        flash('Cannot cancel this booking.', 'danger')
        return redirect(url_for('parent_bookings'))
    
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
    
    mysql.connection.commit()
    cur.close()
    
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('parent_bookings'))

@app.route('/parent/booking/<int:booking_id>/review', methods=['GET', 'POST'])
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
        return redirect(url_for('parent_bookings'))
    
    cur.execute("SELECT id FROM reviews WHERE booking_id = %s", (booking_id,))
    if cur.fetchone():
        flash('You have already reviewed this booking.', 'warning')
        return redirect(url_for('parent_bookings'))
    
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
        
        mysql.connection.commit()
        cur.close()
        
        flash('Review submitted successfully!', 'success')
        return redirect(url_for('parent_bookings'))
    
    cur.close()
    return render_template('parent/review.html', booking=booking)

@app.route('/parent/messages')
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

@app.route('/parent/messages/<int:user_id>')
@login_required
@role_required(['parent'])
def parent_chat(user_id):
    cur = get_db_connection()
    
    cur.execute("SELECT id, full_name, profile_image FROM users WHERE id = %s", (user_id,))
    other_user = cur.fetchone()
    
    if not other_user:
        flash('User not found.', 'danger')
        return redirect(url_for('parent_messages'))
    
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

@app.route('/parent/messages/send', methods=['POST'])
@login_required
@role_required(['parent'])
def send_message():
    receiver_id = request.form.get('receiver_id')
    message_text = request.form.get('message_text')
    booking_id = request.form.get('booking_id')
    
    if not receiver_id or not message_text:
        flash('Invalid message.', 'danger')
        return redirect(url_for('parent_messages'))
    
    cur = get_db_connection()
    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, booking_id, message_text)
        VALUES (%s, %s, %s, %s)
    """, (session['user_id'], receiver_id, booking_id if booking_id else None, message_text))
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('parent_chat', user_id=receiver_id))

@app.route('/parent/notifications')
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

#BABYSITTER ROUTES

@app.route('/babysitter/dashboard')
@login_required
@role_required(['babysitter'])
def babysitter_dashboard():
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    
    if not profile:
        flash('Profile not found.', 'danger')
        return redirect(url_for('logout'))
    
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

@app.route('/babysitter/profile', methods=['GET', 'POST'])
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
            return redirect(url_for('babysitter_profile_edit'))
        
        # Validate hourly_rate range
        if hourly_rate:
            try:
                hourly_rate = float(hourly_rate)
                if hourly_rate < 300 or hourly_rate > 2000:
                    flash('Hourly rate must be between Rs. 300 and Rs. 2,000.', 'danger')
                    return redirect(url_for('babysitter_profile_edit'))
            except (ValueError, TypeError):
                flash('Please enter a valid hourly rate.', 'danger')
                return redirect(url_for('babysitter_profile_edit'))
        
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
            return redirect(url_for('babysitter_profile_edit'))
        
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
                filename = f"user_{session['user_id']}_{secure_filename(file.filename)}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                cur.execute("UPDATE users SET profile_image = %s WHERE id = %s",
                          (filename, session['user_id']))
                mysql.connection.commit()
        
        return redirect(url_for('babysitter_profile_edit'))
    
    cur.execute("""
        SELECT u.*, bp.*
        FROM users u
        LEFT JOIN babysitter_profiles bp ON u.id = bp.user_id
        WHERE u.id = %s
    """, (session['user_id'],))
    user = cur.fetchone()
    cur.close()
    
    return render_template('babysitter/profile.html', user=user)

@app.route('/babysitter/verification', methods=['GET', 'POST'])
@login_required
@role_required(['babysitter'])
def babysitter_verification():
    cur = get_db_connection()
    
    if request.method == 'POST':
        cnic_number = request.form.get('cnic_number', '').strip()
        
        # Validate CNIC format (XXXXX-XXXXXXX-X)
        if not cnic_number:
            flash('Please enter your CNIC number.', 'danger')
            return redirect(url_for('babysitter_verification'))
        
        cnic_cleaned = cnic_number.replace('-', '')
        if not cnic_cleaned.isdigit() or len(cnic_cleaned) != 13:
            flash('Please enter a valid CNIC number (e.g. 12345-1234567-1).', 'danger')
            return redirect(url_for('babysitter_verification'))
        
        cnic_front = None
        if 'cnic_front' in request.files:
            file = request.files['cnic_front']
            if file and allowed_file(file.filename):
                cnic_front = f"cnic_front_{session['user_id']}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], cnic_front))
        
        cnic_back = None
        if 'cnic_back' in request.files:
            file = request.files['cnic_back']
            if file and allowed_file(file.filename):
                cnic_back = f"cnic_back_{session['user_id']}_{secure_filename(file.filename)}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], cnic_back))
        
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
        return redirect(url_for('babysitter_verification'))
    
    cur.execute("""
        SELECT cnic_number, cnic_front_image, cnic_back_image, 
               verification_status, background_check_status
        FROM babysitter_profiles
        WHERE user_id = %s
    """, (session['user_id'],))
    verification = cur.fetchone()
    cur.close()
    
    return render_template('babysitter/verification.html', verification=verification)

@app.route('/babysitter/availability', methods=['GET', 'POST'])
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
                return redirect(url_for('babysitter_availability'))
            
            # Validate day_of_week range
            try:
                day_of_week = int(day_of_week)
                if day_of_week < 0 or day_of_week > 6:
                    flash('Invalid day of week.', 'danger')
                    return redirect(url_for('babysitter_availability'))
            except (ValueError, TypeError):
                flash('Invalid day of week.', 'danger')
                return redirect(url_for('babysitter_availability'))
            
            # Validate end_time > start_time
            try:
                st = datetime.strptime(start_time, '%H:%M')
                et = datetime.strptime(end_time, '%H:%M')
                if et <= st:
                    flash('End time must be after start time.', 'danger')
                    return redirect(url_for('babysitter_availability'))
            except ValueError:
                flash('Invalid time format.', 'danger')
                return redirect(url_for('babysitter_availability'))
            
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
        
        return redirect(url_for('babysitter_availability'))
    
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

@app.route('/babysitter/bookings')
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

@app.route('/babysitter/booking/<int:booking_id>/<action>')
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
        return redirect(url_for('babysitter_bookings'))
    
    if action == 'accept':
        cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
        message = 'Booking accepted successfully!'
    elif action == 'reject':
        cur.execute("UPDATE bookings SET status = 'rejected' WHERE id = %s", (booking_id,))
        message = 'Booking rejected.'
    elif action == 'complete':
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
        return redirect(url_for('babysitter_bookings'))
    
    cur.execute("""
        INSERT INTO notifications (user_id, title, message, type, reference_id)
        VALUES (%s, %s, %s, 'booking', %s)
    """, (booking['parent_id'], f'Booking {action.title()}ed', 
          f'Your booking has been {action}ed by the babysitter', booking_id))
    
    mysql.connection.commit()
    cur.close()
    
    flash(message, 'success')
    return redirect(url_for('babysitter_bookings'))

@app.route('/babysitter/earnings')
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

@app.route('/babysitter/withdraw', methods=['POST'])
@login_required
@role_required(['babysitter'])
def request_withdrawal():
    try:
        amount = float(request.form.get('amount', 0))
    except (ValueError, TypeError):
        flash('Please enter a valid amount.', 'danger')
        return redirect(url_for('babysitter_earnings'))
    
    payment_method = request.form.get('payment_method')
    
    cur = get_db_connection()
    
    cur.execute("SELECT id FROM babysitter_profiles WHERE user_id = %s", (session['user_id'],))
    profile = cur.fetchone()
    babysitter_id = profile['id']
    
    if amount < 1000:
        flash('Minimum withdrawal amount is Rs. 1,000.', 'warning')
        return redirect(url_for('babysitter_earnings'))
    
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
        return redirect(url_for('babysitter_earnings'))
    
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
    return redirect(url_for('babysitter_earnings'))

@app.route('/babysitter/messages')
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

@app.route('/babysitter/messages/<int:user_id>')
@login_required
@role_required(['babysitter'])
def babysitter_chat(user_id):
    cur = get_db_connection()
    
    cur.execute("SELECT id, full_name, profile_image FROM users WHERE id = %s", (user_id,))
    other_user = cur.fetchone()
    
    if not other_user:
        flash('User not found.', 'danger')
        return redirect(url_for('babysitter_messages'))
    
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

@app.route('/babysitter/messages/send', methods=['POST'])
@login_required
@role_required(['babysitter'])
def babysitter_send_message():
    receiver_id = request.form.get('receiver_id')
    message_text = request.form.get('message_text')
    booking_id = request.form.get('booking_id')
    
    if not receiver_id or not message_text:
        flash('Invalid message.', 'danger')
        return redirect(url_for('babysitter_messages'))
    
    cur = get_db_connection()
    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, booking_id, message_text)
        VALUES (%s, %s, %s, %s)
    """, (session['user_id'], receiver_id, booking_id if booking_id else None, message_text))
    
    mysql.connection.commit()
    cur.close()
    
    return redirect(url_for('babysitter_chat', user_id=receiver_id))

@app.route('/babysitter/notifications')
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

#ADMIN ROUTES

@app.route('/admin/dashboard')
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

@app.route('/admin/users')
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

@app.route('/admin/user/<int:user_id>/<action>')
@login_required
@role_required(['admin'])
def admin_user_action(user_id, action):
    cur = get_db_connection()
    
    if action not in ['activate', 'deactivate', 'verify']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin_users'))
        
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
    
    return redirect(url_for('admin_users'))

@app.route('/admin/verifications')
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

@app.route('/admin/verification/<int:profile_id>/<action>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_verify_profile(profile_id, action):
    notes = request.form.get('notes', '')
    
    cur = get_db_connection()
    
    if action not in ['approve', 'reject']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin_verifications'))
        
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
    
    return redirect(url_for('admin_verifications'))

@app.route('/admin/bookings')
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

@app.route('/admin/withdrawals')
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

@app.route('/admin/withdrawal/<int:withdrawal_id>/<action>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_process_withdrawal(withdrawal_id, action):
    notes = request.form.get('notes', '')
    
    cur = get_db_connection()
    
    if action not in ['approve', 'reject', 'complete']:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin_withdrawals'))
        
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
    
    return redirect(url_for('admin_withdrawals'))

@app.route('/admin/analytics')
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

@app.route('/admin/settings', methods=['GET', 'POST'])
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
        return redirect(url_for('admin_settings'))
    
    cur.execute("SELECT * FROM settings")
    settings = cur.fetchall()
    cur.close()
    
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/logs')
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

@app.route('/api/notifications/unread')
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

@app.route('/api/messages/unread')
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

#MAIN
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)