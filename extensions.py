from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect

mysql = MySQL()
csrf = CSRFProtect()
