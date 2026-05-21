from flask import Flask
import os
import secrets
from extensions import mysql, csrf, limiter, mail, socketio
from routes.public import public_bp
from routes.auth import auth_bp
from routes.parent import parent_bp
from routes.babysitter import babysitter_bp
from routes.admin import admin_bp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
    app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
    app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
    app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
    app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'babycare_db')
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['SECURE_UPLOAD_FOLDER'] = 'uploads/secure'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Ensure upload directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SECURE_UPLOAD_FOLDER'], exist_ok=True)

    # Flask-Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))      # 465=SSL, 587=TLS
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False') == 'True'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'saadsaeed072@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'kfukvcaskvahelci')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'saadsaeed072@gmail.com')


    # Initialize extensions
    mysql.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    socketio.init_app(app)  

    @app.context_processor
    def inject_globals():
        return {
            'datetime': datetime,
            'current_year': datetime.now().year,
            'app_name': 'BabyCare',
            'app_tagline': 'Trusted Childcare for Pakistani Families',

        }

    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(babysitter_bp)
    app.register_blueprint(admin_bp)

    @socketio.on('connect')
    def handle_connect():
        from flask import session
        if 'user_id' in session:
            import flask_socketio
            flask_socketio.join_room(f"user_{session['user_id']}")
            print(f"User {session['user_id']} connected and joined room user_{session['user_id']}")

    @socketio.on('location_update')
    def handle_location_update(data):
        from flask import session
        import flask_socketio
        # Expected data: {'lat': float, 'lng': float, 'booking_id': int, 'parent_id': int}
        if 'user_id' in session and session.get('user_type') == 'babysitter':
            parent_id = data.get('parent_id')
            if parent_id:
                # Forward the babysitter's location directly to the parent's room
                flask_socketio.emit('babysitter_location', data, to=f"user_{parent_id}")

    return app

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True)
