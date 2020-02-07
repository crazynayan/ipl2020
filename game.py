import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-cloud.json'

from flask_app.user import User
from flask_app.player import Player

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