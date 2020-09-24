import json
from typing import List, Dict, Tuple

import requests

from config import Config
from flask_app.match_score import MatchPlayer, ScoreData
from flask_app.player import Player
from flask_app.schedule import schedule, Match
from flask_app.team import UserTeam
from flask_app.user import User


def get_mock_score(match: Match) -> Dict:
    try:
        with open(f"source/{match.file_name}") as score_file:
            score_data = json.load(score_file)
    except FileNotFoundError:
        score_data = cache_request(match)
    return score_data


def cache_request(match: Match) -> Dict:
    score_data = get_score(match)
    if score_data:
        with open(f"source/{match.file_name}", "w") as score_file:
            json.dump(score_data, score_file, indent=2)
    return score_data


def get_score(match: Match) -> Dict:
    response = requests.get("https://cricapi.com/api/fantasySummary",
                            params={"apikey": Config.API_KEY, "unique_id": match.unique_id})
    score_data = response.json()
    if "creditsLeft" in score_data:
        print(f"Credits Left: {score_data['creditsLeft']}")
    if "data" not in score_data:
        print(score_data)
        return dict()
    return score_data


def update_match_points():
    matches: List[Match] = schedule.get_matches_being_played()
    if not matches:
        print("Score: No match currently in progress")
        return
    teams = [team for match in matches for team in match.teams]
    players: List[Player] = Player.objects.filter("team", Player.objects.IN, teams).get()
    updated_players = list()
    user_teams: List[UserTeam] = UserTeam.objects.filter("game_week", ">=", schedule.get_game_week() - 1).get()
    updated_teams = list()
    match_ids = [match.unique_id for match in matches]
    match_players: List[MatchPlayer] = MatchPlayer.objects.filter("match_id", MatchPlayer.objects.IN, match_ids).get()
    updated_match_players = list()
    created_match_players = list()
    for match in matches:
        score_data = get_mock_score(match) if Config.USE_MOCK_SCORE else get_score(match)
        if not score_data:
            continue
        score_data = ScoreData(score_data["data"])
        match_id = str(match.unique_id)
        playing_xi: List[Tuple[str, str]] = score_data.get_playing_xi()
        for player_data in playing_xi:
            player = next((player for player in players if player.pid == player_data[0]), None)
            if not player:
                print(f"Player {player_data[1]} ({player_data[0]}) not found")
                continue
            game_week = schedule.get_game_week_last_match_played(player.team)
            if not game_week:
                continue
            user_team: UserTeam = next(team for team in user_teams if team.player_name == player.name and
                                       team.game_week == game_week)
            match_player = next((mp for mp in match_players if mp.player_id == player_data[0] and
                                 mp.match_id == match_id), None)
            if not match_player:
                match_player = MatchPlayer()
                match_player.player_id = player_data[0]
                match_player.player_name = player.name
                match_player.team = player.team
                match_player.match_id = match_id
                match_player.owner = player.owner
                match_player.gameweek = game_week
                match_player.type = user_team.type
                match_player.update_scores(score_data)
                created_match_players.append(match_player)
            else:
                match_player.update_scores(score_data)
                updated_match_players.append(match_player)
            score = match_player.total_points
            if match_id in player.scores and player.scores[match_id] == score:
                continue
            if match_id not in player.scores and score == 0:
                continue
            player.scores[match_id] = score
            player.score = sum(score for _, score in player.scores.items())
            updated_players.append(player)
            user_team.update_match_score(match_id, score)
            updated_teams.append(user_team)
            user_team_next_gw: UserTeam = next((team for team in user_teams if team.player_name == player.name and
                                                team.game_week == user_team.game_week + 1), None)
            if user_team_next_gw:
                user_team_next_gw.final_score = user_team_next_gw.previous_week_score = user_team.final_score
                updated_teams.append(user_team_next_gw)
            print(f"{player.name}: points update to {score}")
    MatchPlayer.objects.create_all(MatchPlayer.objects.to_dicts(created_match_players))
    print(f"MatchPlayer: {len(created_match_players)} players created")
    MatchPlayer.objects.save_all(updated_match_players)
    print(f"MatchPlayer: {len(updated_match_players)} players updated")
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
