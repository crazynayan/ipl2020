import os
from base64 import b64encode

from flask import Flask
from flask_login import LoginManager


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b64encode(os.urandom(24)).decode()
    IMAGES = set(os.listdir('flask_app/static/images'))
    SCORE_2019 = 21154
    PLAYERS_2019 = 128
    COST_2019 = 51395
    TOTAL_COST = 61265
    PLAYERS_COST = 151
    BALANCE = 5580
    USER_LIST = {'NZ', 'MB', 'PP', 'VP', 'RD', 'NU', 'AG', 'SN', 'AS', 'HJ', 'SG'}
    USER_COUNT = len(USER_LIST)
    TOTAL_PLAYERS = 189


ipl_app: Flask = Flask(__name__)
ipl_app.config.from_object(Config)
login = LoginManager(ipl_app)
login.login_view = 'login'
login.login_message = 'Thanks for playing'

# noinspection PyPep8
from flask_app import routes
from flask_app.user import login, logout
