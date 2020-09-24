import os
from datetime import datetime

from config import Config

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-cloud.json'

from scoring import update_match_points
from flask_app.schedule import schedule
from flask_app.team import UserTeam


def set_test_date(data: dict):
    test_date = data.get('test_date', None)
    if not test_date:
        return
    Config.TEST_DATE = datetime.strptime(test_date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=Config.INDIA_TZ)
    return


def update_scores(data: dict, _):
    set_test_date(data)
    if not schedule.get_game_week():
        print("Error: SFL gameweek has not yet started")
        return
    update_match_points()
    return


def create_game_week(data: dict, _):
    set_test_date(data)
    UserTeam.create_game_week()
    return
