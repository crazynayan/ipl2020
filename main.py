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
from flask_app.user import User

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-cloud.json', scope)


def get_player_score(scores: List[dict], player: Player) -> float:
    score = next((score for score in scores if score['ipl_name'] == player.ipl_name), None)
    return score['score'] if score else 0.0


def set_test_date(data: dict):
    test_date = data.get('test_date', None)
    if not test_date:
        return
    Config.TEST_DATE = datetime.strptime(test_date, '%Y-%m-%d %H:%M:%S').replace(tzinfo=Config.INDIA_TZ)
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
    players: List[Player] = Player.objects.get()
    player_names = [player.name for player in players]
    scores = [score for score in scores if score['ipl_name'] in player_names]
    if sum(score['score'] for score in scores) == sum(player.score for player in players):
        print('Sheet: All scores matched and no updates done')
        return
    user_teams: List[UserTeam] = UserTeam.objects.filter("game_week", ">=", schedule.get_game_week() - 1).get()
    stop_game_week = UserTeam.last_game_week() + 1
    updated_players = list()
    updated_teams = list()
    for player in players:
        sheet_score = get_player_score(scores, player)
        if player.score == sheet_score:
            continue
        game_week = schedule.get_game_week_last_match_played(player.team)
        if not game_week:
            continue
        user_team = next(team for team in user_teams if team.player_name == player.name and team.game_week == game_week)
        if not user_team.update_score(player, sheet_score - player.score):
            continue
        updated_teams.append(user_team)
        player.score = sheet_score
        updated_players.append(player)
        for future_gw in range(user_team.game_week + 1, stop_game_week):
            user_team_gw: UserTeam = next(team for team in user_teams
                                          if team.player_name == player.name and team.game_week == future_gw)
            if user_team_gw:
                user_team_gw.final_score = user_team.final_score
                updated_teams.append(user_team_gw)
        print(f"{player.name}: points update to {player.score}")
    if not updated_players:
        print("Error: No updates done")
        return
    Player.objects.save_all(updated_players)
    print(f"Player: {len(updated_players)} players updated")
    UserTeam.objects.save_all(updated_teams)
    print(f"UserTeam: {len(updated_teams)} user teams updated")
    current_gw = schedule.get_game_week()
    # Update points for all users
    updated_users = list()
    for user in User.objects.get():
        players_owned = [user_team for user_team in user_teams if user_team.owner == user.username and
                         user_team.game_week == current_gw]
        points = sum(user_team.final_score for user_team in players_owned)
        if points != user.points:
            user.points = points
            updated_users.append(user)
    User.objects.save_all(updated_users)
    print(f"User: {len(updated_users)} users's points updated")
    return


def create_game_week(data: dict, _):
    set_test_date(data)
    message = UserTeam.create_game_week()
    print(f'{message}')
