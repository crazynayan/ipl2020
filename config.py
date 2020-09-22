import os
from datetime import datetime

from dateutil.tz import gettz

from secrets import SecretConfig


class Config(SecretConfig):
    IMAGES = set(os.listdir("flask_app/static/images"))
    SCORE_2019 = 21154
    PLAYERS_2019 = 128
    COST_2019 = 51395
    TOTAL_COST = 61265
    PLAYERS_COST = 151
    BALANCE = 6140
    USER_LIST = {"NZ": "Nayan Zaveri", "MB": "Manish Bhatt", "PP": "Pranay Patil", "VP": "Vinayak Patil",
                 "RD": "Ravi D'Lima", "FA": "Faisal Ansari", "AS": "Arunesh Shah", "RK": "Raheem Khan",
                 "HJ": "Hitendra Jain", "SG": "Sagar Ghadage"}
    TEAMS = {"Mumbai Indians": "MI", "Chennai Super Kings": "CSK", "Delhi Capitals": "DC", "Kings XI Punjab": "KXIP",
             "Royal Challengers Bangalore": "RCB", "TBD": "TBD", "Kolkata Knight Riders": "KKR",
             "Sunrisers Hyderabad": "SRH", "Rajasthan Royals": "RR"}
    DATE, UNIQUE_ID, HOME_TEAM, AWAY_TEAM = "Date", "Unique Id", "Home Team", "Away Team"
    NORMAL = "Normal"
    CAPTAIN = "Captain"
    SUB = "Sub"
    MULTIPLIER = {NORMAL: 1.0, CAPTAIN: 2.0, SUB: 0.5}
    ROUND, MATCH_NO = "Gameweek", "Match No"
    USER_COUNT = len(USER_LIST)
    TOTAL_PLAYERS = 189
    INDIA_TZ = gettz("Asia/Kolkata")
    GAME_WEEK_START = datetime(year=2020, month=9, day=18, hour=19, tzinfo=INDIA_TZ)
    GAME_WEEK_2_CUT_OFF = datetime(year=2020, month=9, day=21, hour=19, tzinfo=INDIA_TZ)
    GAME_WEEK_9_CUT_OFF = datetime(year=2020, month=11, day=4, hour=19, tzinfo=INDIA_TZ)
    TEST_DATE = None
    USE_MOCK_SCORE = False


def today() -> datetime:
    return Config.TEST_DATE if Config.TEST_DATE else datetime.now(tz=Config.INDIA_TZ)
