import os
from datetime import datetime
from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import Config

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-cloud.json'

from flask_app.schedule import schedule
from flask_app.player import Player
from flask_app.team import UserTeam

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-cloud.json', scope)


def get_player_score(scores: List[dict], player: Player) -> float:
    score = next((score for score in scores if score['ipl_name'] == player.ipl_name), None)
    return score['score'] if score else 0.0


def set_test_date(data: dict):
    test_date = data.get('test_date', None)
    if not test_date:
        return
    Config.TEST_DATE = datetime.strptime(test_date, '%Y-%m-%d %H:%M:%S')
    Config.TEST_DATE = Config.TEST_DATE.replace(tzinfo=Config.INDIA_TZ)
    return


def update_scores(data: dict, _):
    set_test_date(data)
    if not schedule.get_game_week():
        print('Error: SFL gameweek has not yet started')
        return
    scores = gspread.authorize(creds).open('IPL2020').worksheet('Scores').get_all_records()
    try:
        scores = [{'ipl_name': score['ipl_name'], 'score': float(score['score'])} for score in scores]
    except (ValueError, KeyError):
        print('Error: Google Sheet is not properly formatted')
        return
    players = Player.objects.get()
    player_names = [player.name for player in players]
    scores = [score for score in scores if score['ipl_name'] in player_names]
    if sum(score['score'] for score in scores) == sum(player.score for player in players):
        print('Sheet: All scores matched and no updates done')
        return
    players = [player for player in players if player.score != get_player_score(scores, player)]
    score_updated = False
    stop_game_week = UserTeam.last_game_week() + 1
    for index, player in enumerate(players):
        sheet_score = get_player_score(scores, player)
        if not sheet_score:
            continue
        user_team = UserTeam.get_last_match_played(player)
        if not user_team:
            continue
        if user_team.update_score(player, sheet_score - player.score):
            UserTeam.sync_final_score(player, user_team.final_score, user_team.game_week + 1, stop_game_week)
            player.score = sheet_score
            player.save()
            score_updated = True
            print(f'{player.name}: {index + 1} of {len(players)} updated')
    if score_updated:
        UserTeam.update_points()
        print('User: All user points updated')
    else:
        print('Error: No updates done')
    return


def create_game_week(data: dict, _):
    set_test_date(data)
    message = UserTeam.create_game_week()
    print(f'{message}')
