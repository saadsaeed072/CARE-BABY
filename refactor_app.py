import os

def refactor():
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # find indices of sections
    sections = {}
    for i, line in enumerate(lines):
        if line.strip() == '#PUBLIC ROUTES':
            sections['public'] = i
        elif line.strip() == '#AUTHENTICATION ROUTES':
            sections['auth'] = i
        elif line.strip() == '#PARENT ROUTES':
            sections['parent'] = i
        elif line.strip() == '#BABYSITTER ROUTES':
            sections['babysitter'] = i
        elif line.strip() == '#ADMIN ROUTES':
            sections['admin'] = i

    route_start = min(sections.values())

    top_part = lines[:route_start]
    public_part = lines[sections['public']:sections['auth']]
    auth_part = lines[sections['auth']:sections['parent']]
    parent_part = lines[sections['parent']:sections['babysitter']]
    babysitter_part = lines[sections['babysitter']:sections['admin']]
    admin_part = lines[sections['admin']:]

    def write_blueprint(name, lines_part):
        os.makedirs('routes', exist_ok=True)
        with open(f'routes/{name}.py', 'w', encoding='utf-8') as f:
            f.write(f"from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app\n")
            f.write(f"from werkzeug.security import generate_password_hash, check_password_hash\n")
            f.write(f"from werkzeug.utils import secure_filename\n")
            f.write(f"from datetime import datetime, timedelta\n")
            f.write(f"import os\n")
            f.write(f"import uuid\n")
            f.write(f"from extensions import mysql\n")
            f.write(f"from utils import get_db_connection, allowed_file, is_valid_email, is_valid_phone, login_required, role_required\n\n")
            f.write(f"{name}_bp = Blueprint('{name}', __name__)\n\n")
            
            for line in lines_part:
                if line.startswith('@app.route'):
                    line = line.replace('@app.route', f'@{name}_bp.route')
                # Replace app.config with current_app.config
                if 'app.config' in line:
                    line = line.replace('app.config', 'current_app.config')
                f.write(line)

    write_blueprint('public', public_part)
    write_blueprint('auth', auth_part)
    write_blueprint('parent', parent_part)
    write_blueprint('babysitter', babysitter_part)
    write_blueprint('admin', admin_part)

    with open('app_new.py', 'w', encoding='utf-8') as f:
        f.write("from flask import Flask\n")
        f.write("import os\n")
        f.write("import secrets\n")
        f.write("from extensions import mysql, csrf\n")
        f.write("from routes.public import public_bp\n")
        f.write("from routes.auth import auth_bp\n")
        f.write("from routes.parent import parent_bp\n")
        f.write("from routes.babysitter import babysitter_bp\n")
        f.write("from routes.admin import admin_bp\n")
        f.write("from datetime import datetime\n")
        f.write("from dotenv import load_dotenv\n\n")
        f.write("load_dotenv()\n\n")
        
        f.write("def create_app():\n")
        f.write("    app = Flask(__name__)\n\n")
        f.write("    # Configuration\n")
        f.write("    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))\n")
        f.write("    app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')\n")
        f.write("    app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')\n")
        f.write("    app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')\n")
        f.write("    app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'babycare_db')\n")
        f.write("    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'\n")
        f.write("    app.config['UPLOAD_FOLDER'] = 'static/uploads'\n")
        f.write("    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024\n\n")
        f.write("    # Initialize extensions\n")
        f.write("    mysql.init_app(app)\n")
        f.write("    csrf.init_app(app)\n\n")
        
        f.write("    @app.context_processor\n")
        f.write("    def inject_globals():\n")
        f.write("        return {\n")
        f.write("            'datetime': datetime,\n")
        f.write("            'current_year': datetime.now().year,\n")
        f.write("            'app_name': 'BabyCare',\n")
        f.write("            'app_tagline': 'Trusted Childcare for Pakistani Families'\n")
        f.write("        }\n\n")
        
        f.write("    # Register blueprints\n")
        f.write("    app.register_blueprint(public_bp)\n")
        f.write("    app.register_blueprint(auth_bp)\n")
        f.write("    app.register_blueprint(parent_bp)\n")
        f.write("    app.register_blueprint(babysitter_bp)\n")
        f.write("    app.register_blueprint(admin_bp)\n\n")
        f.write("    return app\n\n")
        
        f.write("app = create_app()\n\n")
        f.write("if __name__ == '__main__':\n")
        f.write("    app.run(debug=True)\n")

if __name__ == "__main__":
    refactor()
    print("Extraction successful!")
