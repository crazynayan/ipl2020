import json
import os
from datetime import datetime
from typing import List

import gspread
from oauth2client.service_account import ServiceAccountCredentials

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-cloud.json'

from flask_app import Config
from flask_app.user import User
from flask_app.player import Player
from flask_app.bid import Bid

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


team_names = {'Mumbai Indians': 'MI', 'Chennai Super Kings': 'CSK', 'Delhi Capitals': 'DC', 'Kings XI Punjab': 'KXIP',
              'Royal Challengers Bangalore': 'RCB', 'Kolkata Knight Riders': 'KKR', 'Sunrisers Hyderabad': 'SRH',
              'Rajasthan Royals': 'RR'}


class Schedule:

    def __init__(self):
        self.teams: list = list()
        self.home_team: str = str()
        self.away_team: str = str()
        self.game_week: int = 0
        self.date: datetime = datetime.utcnow()
        self.match: int = 0


def prepare_schedule() -> List[Schedule]:
    with open('source/schedule.txt') as file:
        lines = file.readlines()
        schedules = list()
        schedule = None
        game_week = match = 1
        prev_line = str()
        for line in lines:
            line = line.strip()
            if line.split()[-1] == 'IST':
                schedule = Schedule()
                date = datetime.strptime(line, '%a %d/%m - %I:%M %p IST')
                schedule.date = datetime(year=2020, month=date.month, day=date.day, hour=date.hour)
                if schedule.date.weekday() == 0:
                    game_week += 1
                schedule.game_week = game_week
                schedule.match = match
                match += 1
            if line.split()[-1] == 'HOME':
                schedules.append(schedule)
            if line in team_names and line != prev_line:
                schedule.teams.append(team_names[line])
                if prev_line in team_names:
                    schedule.away_team = team_names[line]
                else:
                    schedule.home_team = team_names[line]
            prev_line = line
        for schedule in schedules:
            print(f"M-{schedule.match:02} GW-{schedule.game_week} {schedule.date.strftime('%a,%d/%m %I:%M %p')}"
                  f" {schedule.home_team} v {schedule.away_team}")
        return schedules
