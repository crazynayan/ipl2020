from datetime import datetime
from datetime import timedelta
from typing import List

from config import Config


class Match:

    def __init__(self):
        self.teams: list = list()
        self.home_team: str = str()
        self.away_team: str = str()
        self.game_week: int = 0
        self.date: datetime = datetime.now()
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
        self.team_names: dict = {'Mumbai Indians': 'MI', 'Chennai Super Kings': 'CSK', 'Delhi Capitals': 'DC',
                                 'Kings XI Punjab': 'KXIP', 'Royal Challengers Bangalore': 'RCB',
                                 'Kolkata Knight Riders': 'KKR', 'Sunrisers Hyderabad': 'SRH', 'Rajasthan Royals': 'RR'}
        self.schedule: List[Match] = self.prepare_schedule()

    def prepare_schedule(self) -> List[Match]:
        with open('source/schedule.txt') as file:
            lines = file.readlines()
        match_list = list()
        game_week = match_number = 1
        prev_line = str()
        match = Match()
        for line in lines:
            line = line.strip()
            if line.split()[-1] == 'IST':
                match = Match()
                date = datetime.strptime(line, '%a %d/%m - %I:%M %p IST')
                match.date = datetime(year=2020, month=date.month, day=date.day, hour=date.hour)
                if match.date.weekday() == Config.GAME_WEEK_START.weekday():
                    game_week += 1
                match.game_week = game_week
                match.number = match_number
                match_number += 1
            if line.split()[-1] == 'HOME':
                match_list.append(match)
            if line in self.team_names and line != prev_line:
                match.teams.append(self.team_names[line])
                if prev_line in self.team_names:
                    match.away_team = self.team_names[line]
                else:
                    match.home_team = self.team_names[line]
            prev_line = line
        return match_list

    @property
    def max_game_week(self):
        return max(self.schedule, key=lambda match: match.game_week).game_week

    def get_game_week(self) -> int:
        date = self.now()
        if date < Config.GAME_WEEK_START:
            return 0
        game_week_start = Config.GAME_WEEK_START
        for game_week in range(1, self.max_game_week + 1):
            if game_week_start <= date < game_week_start + timedelta(days=7):
                return game_week
            game_week_start += timedelta(days=7)
        return self.max_game_week + 1

    @staticmethod
    def get_cut_off(game_week: int) -> datetime:
        if game_week <= 0:
            return Config.GAME_WEEK_START
        return Config.GAME_WEEK_START + timedelta(days=7 * (game_week - 1))

    def get_matches(self, team: str, game_week: int) -> List[str]:
        matches = [match for match in self.schedule if game_week == match.game_week and team in match.teams]
        return [f"{match.date.strftime('%d/%m')} v {match.get_opponent(team)} "
                f"({'H' if team == match.home_team else 'A'})" for match in matches]

    def can_create_game_week(self, game_week: int) -> bool:
        return True if self.now() >= self.get_cut_off(game_week) else False

    def match_played(self, dd_mm: str, team: str) -> bool:
        try:
            match_date = datetime.strptime(dd_mm, '%d/%m')
        except ValueError:
            return False
        match = next((match for match in self.schedule if match.date.day == match_date.day and
                      match.date.month == match_date.month and team in match.teams), None)
        if not match:
            return False
        return True if self.now() > match.date else False

    def get_game_week_last_match_played(self, team: str) -> int:
        match = next((match for match in reversed(self.schedule) if team in match.teams and self.now() > match.date),
                     None)
        return match.game_week if match else 0

    @staticmethod
    def now():
        return Config.TEST_DATE or datetime.now()


schedule = _Schedule()
