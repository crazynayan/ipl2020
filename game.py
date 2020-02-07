import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials

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
