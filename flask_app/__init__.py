from flask import Flask
from flask_login import LoginManager

from config import Config

ipl_app: Flask = Flask(__name__)
ipl_app.config.from_object(Config)
login = LoginManager(ipl_app)
login.login_view = 'login'
login.login_message = 'Thanks for playing'

# noinspection PyPep8
from flask_app import routes
from flask_app.user import login, logout
