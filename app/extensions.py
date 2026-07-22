from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect


db = SQLAlchemy(session_options={"expire_on_commit": False})
login_manager = LoginManager()
csrf = CSRFProtect()
