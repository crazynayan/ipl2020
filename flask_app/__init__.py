import os
from base64 import b64encode

from flask import Flask
from flask_login import LoginManager


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b64encode(os.urandom(24)).decode()


ipl_app: Flask = Flask(__name__)
ipl_app.config.from_object(Config)
login = LoginManager(ipl_app)
login.login_view = 'login'
login.login_message = 'Thanks for playing'

# noinspection PyPep8
from flask_app import routes
from flask_app.user import login, logout
