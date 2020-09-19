import csv
import json
import os
import random
from datetime import datetime
from typing import List, Dict

import gspread
import requests
from dateutil.tz import tzutc
from oauth2client.service_account import ServiceAccountCredentials
from requests import Response

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-cloud.json"

from scoring import update_match_scores
from flask_app import Config
from flask_app.user import User
from flask_app.player import Player
from flask_app.bid import Bid
from flask_app.schedule import schedule
from flask_app.team import UserTeam

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-cloud.json", scope)
headers = ("name", "cost", "base", "country", "type", "ipl2019_score", "team")


def players2019():
    with open("source/players2019.json") as file:
        player_list: list = json.load(file)
    sheet = gspread.authorize(creds).open("IPL2020").worksheet("Players")
    cell_range = sheet.range(f"A1:G{len(player_list) + 1}")
    index = 0
    for header in headers:
        cell_range[index].value = header
        index += 1
    for player in player_list:
        for header in headers:
            cell_range[index].value = player[header]
            index += 1
    sheet.update_cells(cell_range)
    print(f"Updated {len(player_list)} players.")
    return


def players2020():
    sheet = gspread.authorize(creds).open("IPL2020").worksheet("Players")
    players = sheet.get_all_records()
    with open("source/players2020.json", "w") as file:
        json.dump(players, file, indent=2)
    print(f"players2020.json file created.")


def users2020():
    sheet = gspread.authorize(creds).open("IPL2020").worksheet("Users")
    users = sheet.get_all_records()
    with open("source/users2020.json", "w") as file:
        json.dump(users, file, indent=2)
    print(f"users2020.json file created.")


def upload():
    print("Starting users upload.")
    User.objects.delete()
    print("All users deleted from firestore.")
    with open("source/users2020.json") as file:
        users = json.load(file)
    for index, user in enumerate(users):
        user_doc: User = User.create_from_dict(user)
        user_doc.set_password(user["password"])
        print(f"Users: {index + 1} of {len(users)} uploaded.")
    print("Starting players upload.")
    Player.objects.delete()
    print("All players deleted from firestore.")
    with open("source/players2020.json") as file:
        players = json.load(file)
    for index, player in enumerate(players):
        player["ipl_name"] = player["name"]
        Player.create_from_dict(player)
        print(f"Players: {index + 1} of {len(players)} uploaded.")
    print("Upload to firestore complete.")


def update_rank():
    print("Calculating Ranks")
    players: List[Player] = Player.objects.get()
    players.sort(key=lambda player_item: -player_item.ipl2019_score)
    for player in players:
        ranked_player = next(rank_player for rank_player in players
                             if rank_player.ipl2019_score == player.ipl2019_score)
        player.ipl2019_rank = players.index(ranked_player) + 1
    players.sort(key=lambda player_item: -player_item.cost)
    for player in players:
        ranked_player = next(rank_player for rank_player in players if rank_player.cost == player.cost)
        player.cost_rank = players.index(ranked_player) + 1
    for index, player in enumerate(players):
        player.save()
        print(f"Players: {index + 1} of {len(players)} updated.")
    print("Rank Update Complete.")


def reset_auction(auto_bid: bool = False, except_users: List[str] = None):
    for user in User.objects.get():
        user.balance = Config.BALANCE
        user.player_count = 0
        user.auto_bid = auto_bid ^ True if except_users and user.username in except_users else auto_bid
        user.save()
    print("User: Balance update complete.")
    players = Player.objects.get()
    for index, player in enumerate(players):
        player.auction_status = str()
        player.bid_order = 0
        player.owner = None
        player.price = 0
        player.save()
        if index % 10 == 0:
            print(f"Player: {index + 1} of {len(players)} updated.")
    print("Player: All players updated.")
    Bid.objects.delete()
    print("Bid: All bids deleted.")


def print_schedule():
    for match in schedule.schedule:
        print(match)


def game_week(date: str):
    print(schedule.get_game_week(datetime(year=2020, month=int(date.split("/")[1]), day=int(date.split("/")[0]),
                                          hour=int(date.split("/")[2]))))


playingXI = {
    "CSK": [
        "Shane Watson",
        "Ravindra Jadeja",
        "Dwayne Bravo",
        "Faf du Plessis",
        "Suresh Raina",
        "Ambati Rayudu",
        "Kedar Jadhav",
        "MS Dhoni",
        "Deepak Chahar",
        "Shardul Thakur",
        "Imran Tahir",
    ],
    "MI": [
        "Hardik Pandya",
        "Krunal Pandya",
        "Kieron Pollard",
        "Suryakumar Yadav",
        "Rohit Sharma",
        "Chris Lynn",
        "Quinton de Kock",
        "Rahul Chahar",
        "Jasprit Bumrah",
        "Lasith Malinga",
        "Dhawal Kulkarni",
    ],
    "KXIP": [
        "Chris Gayle",
        "Mayank Agarwal",
        "Mandeep Singh",
        "Karun Nair",
        "Mohammed Shami",
        "Sheldon Cottrell",
        "Krishnappa Gowtham",
        "Lokesh Rahul",
        "Sarfaraz Khan",
        "Glenn Maxwell",
        "Chris Jordan",
    ],
    "DC": [
        "Marcus Stoinis",
        "Keemo Paul",
        "Chris Woakes",
        "Shikhar Dhawan",
        "Shreyas Iyer",
        "Ajinkya Rahane",
        "Prithvi Shaw",
        "Kagiso Rabada",
        "Ishant Sharma",
        "Ravichandran Ashwin",
        "Rishabh Pant",
    ],
    "RCB": [
        "Moeen Ali",
        "Chris Morris",
        "Washington Sundar",
        "Shivam Dube",
        "AB De villiers",
        "Virat Kohli",
        "Aaron Finch",
        "Navdeep Saini",
        "Umesh Yadav",
        "Yuzvendra Chahal",
        "Parthiv Patel",
    ],
    "KKR": [
        "Andre Russell",
        "Sunil Narine",
        "Pat Cummins",
        "Nitish Rana",
        "Shubman Gill",
        "Rahul Tripathi",
        "Eoin Morgan",
        "Prasidh Krishna",
        "Sandeep Warrier",
        "Kuldeep Yadav",
        "Dinesh Karthik",
    ],
    "SRH": [
        "Vijay Shankar",
        "Mohammad Nabi",
        "David Warner",
        "Manish Pandey",
        "Kane Williamson",
        "Khaleel Ahmed",
        "Bhuvneshwar Kumar",
        "Sandeep Sharma",
        "Siddarth Kaul",
        "Rashid Khan",
        "Jonny Bairstow",
    ],
    "RR": [
        "Jofra Archer",
        "Ben Stokes",
        "Riyan Parag",
        "Steve Smith",
        "Robin Uthappa",
        "Jaydev Unadkat",
        "Varun Aaron",
        "Ankit Rajpoot",
        "Shreyas Gopal",
        "Jos Buttler",
        "Sanju Samson",
    ]
}

max_score = int(34 * 2)


def update_score(match_list: List[int]):
    sheet = gspread.authorize(creds).open("IPL2020").worksheet("Scores")
    cell_range = sheet.range(f"A1:B190")
    for index in range(3, 380, 2):
        cell_range[index].value = float(cell_range[index].value)
    for match_number in match_list:
        match = next(match for match in schedule.schedule if match_number == match.number)
        players = [player_name for team_name, player_list in playingXI.items() for player_name in player_list
                   if team_name in match.teams]
        for player_name in players:
            score = 2.0 if random.random() < 0.3 else random.randrange(4, max_score * 2 + 1) / 2
            index = next(index for index in range(2, 380, 2) if cell_range[index].value == player_name)
            cell_range[index + 1].value += score
    sheet.update_cells(cell_range)
    print(f"Updated scores for all matches.")
    return


def reset_score():
    players = Player.objects.get()
    for player in players:
        player.score = 0
        for match_id in player.scores:
            player.scores[match_id] = 0
    users = User.objects.get()
    for user in users:
        user.points = 0.0
    teams: List[UserTeam] = UserTeam.objects.filter("final_score", ">", 0).get()
    for user_team in teams:
        user_team.final_score = 0.0
        user_team.previous_week_score = 0.0
        for match in user_team.matches:
            match["score"] = 0.0
    Player.objects.save_all(players)
    User.objects.save_all(users)
    UserTeam.objects.save_all(teams)
    print(f"All players score zeroed.")


def show_player_not_in_db():
    scores = gspread.authorize(creds).open("IPL2020").worksheet("Scores").get_all_records()
    player_names = [player.name for player in Player.objects.get()]
    scores = [score for score in scores if score["ipl_name"] not in player_names]
    if not scores:
        print("All players present")
    else:
        for score in scores:
            print(score["ipl_name"])
    return


def update_schedule_file():
    response: Response = requests.get("https://cricapi.com/api/matches", params={"apikey": Config.API_KEY})
    matches: List[dict] = response.json()["matches"]
    schedules: List[dict] = list()
    match_number = gameweek = 1
    for match in matches:
        if match["team-1"] not in Config.TEAMS:
            continue
        match_date = datetime.fromisoformat(match["dateTimeGMT"][:-1]).replace(tzinfo=tzutc())
        match_date = match_date.astimezone(Config.INDIA_TZ)
        if match_date.weekday() == Config.GAME_WEEK_2_CUT_OFF.weekday():
            gameweek += 1
        schedules.append({
            Config.ROUND: gameweek,
            Config.DATE: match_date.strftime("%d/%m/%Y %H:%M"),
            Config.HOME_TEAM: match["team-1"],
            Config.AWAY_TEAM: match["team-2"],
            Config.UNIQUE_ID: match["unique_id"],
            Config.MATCH_NO: match_number
        })
        match_number += 1
    fieldnames = [Config.MATCH_NO, Config.ROUND, Config.DATE, Config.HOME_TEAM, Config.AWAY_TEAM, Config.UNIQUE_ID]
    with open("source/schedule.csv", "w", newline="") as schedule_file:
        writer = csv.DictWriter(schedule_file, fieldnames=fieldnames)
        writer.writeheader()
        for match in schedules:
            writer.writerow(match)
    print("Schedule file created")


def update_players():
    mi_csk, dc_kxip, srh_rcb, rr_kkr = 1216492, 1216493, 1216534, 1216504
    match_ids = [mi_csk, dc_kxip, srh_rcb, rr_kkr]
    players: List[Dict] = list()
    for unique_id in match_ids:
        response: Response = requests.get("https://cricapi.com/api/fantasySquad",
                                          params={"apikey": Config.API_KEY, "unique_id": unique_id})
        squad: List[Dict] = response.json()["squad"]
        for team in squad:
            players.extend([{**player, "team": Config.TEAMS[team["name"]]} for player in team["players"]])
    for player in players:
        print(player)
    with open("source/players_api.json", "w") as player_file:
        json.dump(players, player_file, indent=2)
    print("player_api.json file created")


def update_api_players():
    with open("source/players_api.json") as player_file:
        api_players: List[Dict] = json.load(player_file)
    db_players: List[Player] = Player.objects.get()
    not_found_players: List[Player] = list()
    updated_players: List[Player] = list()
    for db_player in db_players:
        db_names = {db_player.name.lower(), db_player.ipl_name.lower()}
        api_player = next((player for player in api_players if player["name"].lower() in db_names), None)
        if not api_player:
            not_found_players.append(db_player)
            continue
        db_player.ipl_name = api_player["name"]
        db_player.pid = str(api_player["pid"])
        updated_players.append(db_player)
    Player.objects.save_all(updated_players)
    print(f"{len(updated_players)} players updated")
    if not not_found_players:
        print("All players synced")
        return
    print("Following players still need to be synced")
    not_found_players.sort(key=lambda player: player.name)
    for player in not_found_players:
        print(player)
    return


def check_api_players():
    with open("source/players_api.json") as player_file:
        api_players: List[Dict] = json.load(player_file)
    db_players: List[Player] = Player.objects.get()
    db_names = [player.ipl_name.lower() for player in db_players]
    for player in api_players:
        if player["name"].lower() not in db_names:
            print(player)
    return


def update_fantasy_score_file():
    response: Response = requests.get("https://cricapi.com/api/fantasySummary",
                                      params={"apikey": Config.API_KEY, "unique_id": 1207770})
    with open("source/fantasy_score.json", "w") as score_file:
        json.dump(response.json(), score_file, indent=2)
    print("fantasy_score.json file created")


def test_update_score():
    update_match_scores()
