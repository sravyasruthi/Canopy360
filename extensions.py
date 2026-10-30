# extensions.py - shared objects used by app.py, models and routes
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()      # database connection
csrf = CSRFProtect()   # protects forms from CSRF attacks