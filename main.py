import os
from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-cloud.json'

from flask_app.schedule import schedule
from flask_app.player import Player
from flask_app.team import UserTeam

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-cloud.json', scope)


def get_player_score(scores: List[dict], player: Player) -> float:
    score = next((score for score in scores if score['ipl_name'] == player.ipl_name), None)
    return score['score'] if score else 0.0


def update_scores(**_):
    if not schedule.get_game_week():
        return False
    scores = gspread.authorize(creds).open('IPL2020').worksheet('Scores').get_all_records()
    try:
        scores = [{'ipl_name': score['ipl_name'], 'score': float(score['score'])} for score in scores]
    except (ValueError, KeyError):
        return False
    players = Player.objects.get()
    player_names = [player.name for player in players]
    scores = [score for score in scores if score['ipl_name'] in player_names]
    if sum(score['score'] for score in scores) == sum(player.score for player in players):
        return False
    players = [player for player in players if player.score != get_player_score(scores, player)]
    score_updated = False
    stop_game_week = UserTeam.last_game_week() + 1
    for player in players:
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
    if score_updated:
        UserTeam.update_points()
    return score_updated


def create_game_week(**_):
    return UserTeam.create_game_week() == str()
