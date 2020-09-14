import csv
from datetime import datetime
from datetime import timedelta
from typing import List

from config import Config, today

DATE, LOCATION, HOME_TEAM, AWAY_TEAM, ROUND = "Date", "Location", "Home Team", "Away Team", "Round Number"


class Match:

    def __init__(self):
        self.teams: list = list()
        self.home_team: str = str()
        self.away_team: str = str()
        self.game_week: int = 0
        self.date: datetime = datetime.now(Config.INDIA_TZ)
        self.number: int = 0

    def __repr__(self):
        return f"M-{self.number:02} GW-{self.game_week} {self.date.strftime('%a,%d/%m %I:%M %p')} " \
               f"{self.home_team} v {self.away_team}"

    def get_opponent(self, team: str) -> str:
        if team not in self.teams:
            return str()
        return self.home_team if team == self.away_team else self.away_team


class _Schedule:

    def __init__(self):
        self.team_names: dict = {"Mumbai Indians": "MI", "Chennai Super Kings": "CSK", "Delhi Capitals": "DC",
                                 "Kings XI Punjab": "KXIP", "Royal Challengers Bangalore": "RCB", "TBD": "TBD",
                                 "Kolkata Knight Riders": "KKR", "Sunrisers Hyderabad": "SRH", "Rajasthan Royals": "RR"}
        self.schedule: List[Match] = self.prepare_schedule()

    def prepare_schedule(self):
        match_list = list()
        schedule_file = open("source/schedule.csv")
        game_week = match_number = 1
        schedule_reader = csv.DictReader(schedule_file)
        for row in schedule_reader:
            match = Match()
            match.date = datetime.strptime(row[DATE], "%d/%m/%Y %H:%M").replace(tzinfo=Config.INDIA_TZ)
            if match.date.weekday() == Config.GAME_WEEK_START.weekday():
                game_week += 1
            match.game_week = game_week if row[ROUND] != "8" else 9
            match.number = match_number
            match_number += 1
            match.home_team = self.team_names[row[HOME_TEAM]]
            match.away_team = self.team_names[row[AWAY_TEAM]]
            match.teams = [match.home_team, match.away_team]
            match_list.append(match)
        schedule_file.close()
        return match_list

    @property
    def max_game_week(self):
        return max(self.schedule, key=lambda match: match.game_week).game_week

    def get_game_week(self) -> int:
        date = today()
        if date <= Config.GAME_WEEK_START:
            return 0
        if Config.GAME_WEEK_START <= date <= Config.GAME_WEEK_1_CUT_OFF:
            return 1
        if date > Config.GAME_WEEK_9_CUT_OFF:
            return self.max_game_week + 1
        game_week_start = Config.GAME_WEEK_START
        for game_week in range(1, self.max_game_week + 1):
            if game_week_start <= date < game_week_start + timedelta(days=7):
                return game_week
            game_week_start += timedelta(days=7)
        return self.max_game_week + 1

    @staticmethod
    def get_cut_off(game_week: int) -> datetime:
        if game_week < 1:
            return Config.GAME_WEEK_START
        if game_week == 1:
            return Config.GAME_WEEK_1_CUT_OFF
        if game_week == 9:
            return Config.GAME_WEEK_9_CUT_OFF
        return Config.GAME_WEEK_START + timedelta(days=7 * (game_week - 1))

    def get_matches(self, team: str, game_week: int) -> List[str]:
        matches = [match for match in self.schedule if game_week == match.game_week and team in match.teams]
        return [f"{match.date.strftime('%d/%m')} v {match.get_opponent(team)} "
                f"({'H' if team == match.home_team else 'A'})" for match in matches]

    def can_create_game_week(self, game_week: int) -> bool:
        return True if today() >= self.get_cut_off(game_week) else False

    def match_played(self, dd_mm: str, team: str) -> bool:
        try:
            match_date = datetime.strptime(dd_mm, '%d/%m')
        except ValueError:
            return False
        match = next((match for match in self.schedule if match.date.day == match_date.day and
                      match.date.month == match_date.month and team in match.teams), None)
        if not match:
            return False
        return True if today() > match.date else False

    def get_game_week_last_match_played(self, team: str) -> int:
        match = next((match for match in reversed(self.schedule) if team in match.teams and today() > match.date),
                     None)
        return match.game_week if match else 0


schedule = _Schedule()
