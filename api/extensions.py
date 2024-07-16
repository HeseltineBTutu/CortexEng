from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_login import LoginManager, login_user, logout_user, login_required

bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
