import json
from typing import List, Dict

import requests

from config import Config
from flask_app.player import Player
from flask_app.schedule import schedule, Match
from flask_app.team import UserTeam
from flask_app.user import User


def get_mock_score(_) -> Dict:
    with open("source/fantasy_score.json") as score_file:
        score_data = json.load(score_file)
    return score_data["data"]


def get_score(match_id: int) -> Dict:
    response = requests.get("https://cricapi.com/api/fantasySummary",
                            params={"apikey": Config.API_KEY, "unique_id": match_id})
    score_data = response.json()
    return score_data["data"]


def get_batting_score(score_data: Dict, pid: str) -> int:
    batting = next((player for team in score_data["batting"] for player in team["scores"]
                    if player["pid"] == pid), None)
    if not batting:
        return 0
    score = batting["R"] + batting["4s"] * 2 + batting["6s"] * 3
    if batting["R"] >= 100:
        score += 20
    if batting["R"] >= 50:
        score += 10
    return score


def get_bowling_score(score_data: Dict, pid: str) -> int:
    bowling = next((player for team in score_data["bowling"] for player in team["scores"]
                    if player["pid"] == pid), None)
    if not bowling:
        return 0
    score = int(bowling["W"]) * 20
    er = float(bowling["Econ"])
    if er < 2.0:
        score += 50
    elif er < 4.0:
        score += 40
    elif er < 6.0:
        score += 30
    elif er < 7.0:
        score += 20
    return score


def get_man_of_the_match_score(score_data: Dict, pid: str) -> int:
    if "man-of-the-match" not in score_data:
        return 0
    if "pid" not in score_data["man-of-the-match"]:
        return 0
    if pid != score_data["man-of-the-match"]["pid"]:
        return 0
    return 50


def calculate_scores() -> Dict[str, List[Player]]:
    matches: List[Match] = schedule.get_matches_being_played()
    if not matches:
        return dict()
    teams = [team for match in matches for team in match.teams]
    players: List[Player] = Player.objects.filter("team", Player.objects.IN, teams).get()
    updated_players = dict()
    for match in matches:
        # Replace the mock with real before deploying
        # score_data = get_mock_score(match.unique_id)
        score_data = get_score(match.unique_id)
        playing_xi_ids = [player["pid"] for team in score_data["team"] for player in team["players"]]
        match_id = str(match.unique_id)
        updated_players[match_id] = list()
        for pid in playing_xi_ids:
            score = get_batting_score(score_data, pid)
            score += get_bowling_score(score_data, pid)
            score += get_man_of_the_match_score(score_data, pid)
            player = next((player for player in players if player.pid == pid), None)
            if not player:
                print(f"Player with pid {pid} not found")
                continue
            if match_id in player.scores and player.scores[match_id] == score:
                continue
            player.scores[match_id] = score
            updated_players[match_id].append(player)
    return updated_players


def update_match_scores():
    player_scores = calculate_scores()
    if not player_scores:
        print("Score: All scores matched and no updates done")
        return
    user_teams: List[UserTeam] = UserTeam.objects.filter("game_week", ">=", schedule.get_game_week() - 1).get()
    updated_teams = list()
    updated_players = list()
    for match_id, players in player_scores.items():
        for player in players:
            game_week = schedule.get_game_week_last_match_played(player.team)
            if not game_week:
                continue
            if not player.scores[match_id]:
                continue
            user_team: UserTeam = next(team for team in user_teams if team.player_name == player.name and
                                       team.game_week == game_week)
            user_team.update_match_score(match_id, player.scores[match_id])
            updated_teams.append(user_team)
            updated_players.append(player)
            user_team_next_gw: UserTeam = next((team for team in user_teams if team.player_name == player.name and
                                                team.game_week == user_team.game_week + 1), None)
            if user_team_next_gw:
                user_team_next_gw.final_score = user_team_next_gw.previous_week_score = user_team.final_score
                updated_teams.append(user_team_next_gw)
            print(f"{player.name}: points update to {player.scores[match_id]}")
    Player.objects.save_all(updated_players)
    print(f"Player: {len(updated_players)} players updated")
    UserTeam.objects.save_all(updated_teams)
    print(f"UserTeam: {len(updated_teams)} user teams updated")
    # Update points for all users
    updated_users = list()
    current_gw = schedule.get_game_week()
    for user in User.objects.get():
        players_owned = [user_team for user_team in user_teams if user_team.owner == user.username and
                         user_team.game_week == current_gw]
        points = sum(user_team.final_score for user_team in players_owned)
        if points != user.points:
            user.points = points
            updated_users.append(user)
    User.objects.save_all(updated_users)
    print(f"User: {len(updated_users)} users's points updated")
