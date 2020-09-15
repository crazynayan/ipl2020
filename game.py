import json
import os
import random
from datetime import datetime
from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import main
from flask_app.team import UserTeam

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = main.os.environ['GOOGLE_APPLICATION_CREDENTIALS']

from flask_app import Config
from flask_app.user import User
from flask_app.player import Player
from flask_app.bid import Bid
from flask_app.schedule import schedule

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('google-cloud.json', scope)
headers = ('name', 'cost', 'base', 'country', 'type', 'ipl2019_score', 'team')


def players2019():
    with open('source/players2019.json') as file:
        player_list: list = json.load(file)
    sheet = gspread.authorize(creds).open('IPL2020').worksheet('Players')
    cell_range = sheet.range(f'A1:G{len(player_list) + 1}')
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
    sheet = gspread.authorize(creds).open('IPL2020').worksheet('Players')
    players = sheet.get_all_records()
    with open('source/players2020.json', 'w') as file:
        json.dump(players, file, indent=2)
    print(f"players2020.json file created.")


def users2020():
    sheet = gspread.authorize(creds).open('IPL2020').worksheet('Users')
    users = sheet.get_all_records()
    with open('source/users2020.json', 'w') as file:
        json.dump(users, file, indent=2)
    print(f"users2020.json file created.")


def upload():
    print('Starting users upload.')
    User.objects.delete()
    print('All users deleted from firestore.')
    with open('source/users2020.json') as file:
        users = json.load(file)
    for index, user in enumerate(users):
        user_doc: User = User.create_from_dict(user)
        user_doc.set_password(user['password'])
        print(f"Users: {index + 1} of {len(users)} uploaded.")
    print('Starting players upload.')
    Player.objects.delete()
    print('All players deleted from firestore.')
    with open('source/players2020.json') as file:
        players = json.load(file)
    for index, player in enumerate(players):
        player['ipl_name'] = player['name']
        Player.create_from_dict(player)
        print(f"Players: {index + 1} of {len(players)} uploaded.")
    print('Upload to firestore complete.')


def update_rank():
    print('Calculating Ranks')
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
    print('Rank Update Complete.')


def reset_auction(auto_bid: bool = False, except_users: List[str] = None):
    for user in User.objects.get():
        user.balance = Config.BALANCE
        user.player_count = 0
        user.auto_bid = auto_bid ^ True if except_users and user.username in except_users else auto_bid
        user.save()
    print('User: Balance update complete.')
    players = Player.objects.get()
    for index, player in enumerate(players):
        player.auction_status = str()
        player.bid_order = 0
        player.owner = None
        player.price = 0
        player.save()
        if index % 10 == 0:
            print(f"Player: {index + 1} of {len(players)} updated.")
    print('Player: All players updated.')
    Bid.objects.delete()
    print("Bid: All bids deleted.")


def print_schedule():
    for match in schedule.schedule:
        print(match)


def game_week(date: str):
    print(schedule.get_game_week(datetime(year=2020, month=int(date.split('/')[1]), day=int(date.split('/')[0]),
                                          hour=int(date.split('/')[2]))))


playingXI = {
    'CSK': [
        'Shane Watson',
        'Ravindra Jadeja',
        'Dwayne Bravo',
        'Faf du Plessis',
        'Suresh Raina',
        'Ambati Rayudu',
        'Kedar Jadhav',
        'MS Dhoni',
        'Deepak Chahar',
        'Shardul Thakur',
        'Imran Tahir',
    ],
    'MI': [
        'Hardik Pandya',
        'Krunal Pandya',
        'Kieron Pollard',
        'Suryakumar Yadav',
        'Rohit Sharma',
        'Chris Lynn',
        'Quinton de Kock',
        'Rahul Chahar',
        'Jasprit Bumrah',
        'Lasith Malinga',
        'Dhawal Kulkarni',
    ],
    'KXIP': [
        'Chris Gayle',
        'Mayank Agarwal',
        'Mandeep Singh',
        'Karun Nair',
        'Mohammed Shami',
        'Sheldon Cottrell',
        'Krishnappa Gowtham',
        'Lokesh Rahul',
        'Sarfaraz Khan',
        'Glenn Maxwell',
        'Chris Jordan',
    ],
    'DC': [
        'Marcus Stoinis',
        'Keemo Paul',
        'Chris Woakes',
        'Shikhar Dhawan',
        'Shreyas Iyer',
        'Ajinkya Rahane',
        'Prithvi Shaw',
        'Kagiso Rabada',
        'Ishant Sharma',
        'Ravichandran Ashwin',
        'Rishabh Pant',
    ],
    'RCB': [
        'Moeen Ali',
        'Chris Morris',
        'Washington Sundar',
        'Shivam Dube',
        'AB De villiers',
        'Virat Kohli',
        'Aaron Finch',
        'Navdeep Saini',
        'Umesh Yadav',
        'Yuzvendra Chahal',
        'Parthiv Patel',
    ],
    'KKR': [
        'Andre Russell',
        'Sunil Narine',
        'Pat Cummins',
        'Nitish Rana',
        'Shubman Gill',
        'Rahul Tripathi',
        'Eoin Morgan',
        'Prasidh Krishna',
        'Sandeep Warrier',
        'Kuldeep Yadav',
        'Dinesh Karthik',
    ],
    'SRH': [
        'Vijay Shankar',
        'Mohammad Nabi',
        'David Warner',
        'Manish Pandey',
        'Kane Williamson',
        'Khaleel Ahmed',
        'Bhuvneshwar Kumar',
        'Sandeep Sharma',
        'Siddarth Kaul',
        'Rashid Khan',
        'Jonny Bairstow',
    ],
    'RR': [
        'Jofra Archer',
        'Ben Stokes',
        'Riyan Parag',
        'Steve Smith',
        'Robin Uthappa',
        'Jaydev Unadkat',
        'Varun Aaron',
        'Ankit Rajpoot',
        'Shreyas Gopal',
        'Jos Buttler',
        'Sanju Samson',
    ]
}

max_score = int(34 * 2)


def update_score(match_list: List[int]):
    sheet = gspread.authorize(creds).open('IPL2020').worksheet('Scores')
    cell_range = sheet.range(f'A1:B190')
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
    sheet = gspread.authorize(creds).open('IPL2020').worksheet('Scores')
    cell_range = sheet.range(f'A1:B190')
    for index in range(3, 380, 2):
        cell_range[index].value = 0.0
    sheet.update_cells(cell_range)
    players = Player.objects.filter('score', '>', 0).get()
    for player in players:
        player.score = 0.0
    users = User.objects.get()
    for user in users:
        user.points = 0.0
    teams: List[UserTeam] = UserTeam.objects.filter("final_score", ">", 0).get()
    for user_team in teams:
        user_team.final_score = 0.0
        for match in user_team.matches:
            match["score"] = 0.0
    Player.objects.save_all(players)
    User.objects.save_all(users)
    UserTeam.objects.save_all(teams)
    print(f"All players score zeroed.")


def show_player_not_in_db():
    scores = gspread.authorize(creds).open('IPL2020').worksheet('Scores').get_all_records()
    player_names = [player.name for player in Player.objects.get()]
    scores = [score for score in scores if score['ipl_name'] not in player_names]
    if not scores:
        print('All players present')
    else:
        for score in scores:
            print(score['ipl_name'])
    return
