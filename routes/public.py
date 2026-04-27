from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import uuid
from extensions import mysql
from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required

public_bp = Blueprint('public', __name__)

#PUBLIC ROUTES 

@public_bp.route('/')
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

@public_bp.route('/about')
def about():
    return render_template('about.html')

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone', '')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        if not name or not email or not subject or not message:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('public.contact'))
        
        # Validate email format
        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('public.contact'))
        
        cur = get_db_connection()
        cur.execute("""
            INSERT INTO contact_messages (name, email, phone, subject, message)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, phone, subject, message))
        mysql.connection.commit()
        cur.close()
        
        flash('Your message has been sent successfully! We will get back to you soon.', 'success')
        return redirect(url_for('public.contact'))
    
    return render_template('contact.html')

@public_bp.route('/help')
def help_center():
    return render_template('help.html')

@public_bp.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@public_bp.route('/search')
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

@public_bp.route('/babysitter/<int:id>')
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
        return redirect(url_for('public.search'))
    
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

@public_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')

@public_bp.route('/terms')
def terms():
    return render_template('terms.html')
