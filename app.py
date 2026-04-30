from flask import Flask
import os
import secrets
from extensions import mysql, csrf, limiter, mail
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
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Flask-Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 465))      # 465=SSL, 587=TLS
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'False') == 'True'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'saadsaeed072@gmail.com')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'kfukvcaskvahelci')  # App Password (no spaces)
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'saadsaeed072@gmail.com')

    # Initialize extensions
    mysql.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    @app.context_processor
    def inject_globals():
        return {
            'datetime': datetime,
            'current_year': datetime.now().year,
            'app_name': 'BabyCare',
            'app_tagline': 'Trusted Childcare for Pakistani Families'
        }

    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(parent_bp)
    app.register_blueprint(babysitter_bp)
    app.register_blueprint(admin_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
