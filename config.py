import os
from base64 import b64encode
from datetime import datetime

from pytz import timezone


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or b64encode(os.urandom(24)).decode()
    IMAGES = set(os.listdir('flask_app/static/images'))
    SCORE_2019 = 21154
    PLAYERS_2019 = 128
    COST_2019 = 51395
    TOTAL_COST = 61265
    PLAYERS_COST = 151
    BALANCE = 6140
    USER_LIST = {'NZ': 'Nayan Zaveri', 'MB': 'Manish Bhatt', 'PP': 'Pranay Patil', 'VP': 'Vinayak Patil',
                 'RD': "Ravi D'Lima", 'FA': 'Faisal Ansari', 'AS': 'Arunesh Shah', 'RK': 'Raheem Khan',
                 'HJ': 'Hitendra Jain', 'SG': 'Sagar Ghadage'}
    USER_COUNT = len(USER_LIST)
    TOTAL_PLAYERS = 189
    INDIA_TZ = timezone('Asia/Kolkata')
    TEST_DATE = None
    GAME_WEEK_START = datetime(year=2020, month=3, day=23, hour=19, tzinfo=INDIA_TZ)
