from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_socketio import SocketIO

mysql = MySQL()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()
socketio: SocketIO = SocketIO(cors_allowed_origins="*")

