import os
from base64 import b64encode
from datetime import datetime


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
    AUCTION_COMPLETE = False
    TEST_DATE = datetime(year=2020, month=4, day=6, hour=20, minute=1)
    GAME_WEEK_START = datetime(year=2020, month=3, day=23, hour=19)
