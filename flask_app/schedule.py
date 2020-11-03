import csv
from datetime import datetime
from datetime import timedelta
from typing import List

from config import Config, today


class Match:

    def __init__(self):
        self.teams: list = list()
        self.home_team: str = str()
        self.away_team: str = str()
        self.game_week: int = 0
        self.date: datetime = datetime.now(Config.INDIA_TZ)
        self.number: int = 0
        self.unique_id: int = 0

    def __repr__(self):
        return f"M-{self.number} GW-{self.game_week} ID-{self.unique_id} {self.date.strftime('%a,%d/%m %I:%M %p')} " \
               f"{self.home_team} v {self.away_team}"

    @property
    def file_name(self):
        return f"m{self.number:02}-{self.home_team.lower()}-{self.away_team.lower()}.json"

    def get_opponent(self, team: str) -> str:
        if team not in self.teams:
            return str()
        return self.home_team if team == self.away_team else self.away_team

    def get_text(self, team):
        return f"{self.date.strftime('%d/%m')} v {self.get_opponent(team)} ({'H' if team == self.home_team else 'A'})"

    @property
    def display(self):
        return f"{self.number}. {self.home_team} v {self.away_team} @  {self.date.strftime('%#d/%m')}"

    @property
    def display_class(self):
        return f"btn btn-block btn-primary {'disabled' if self.date > today() else str()}"


class _Schedule:

    def __init__(self):
        self.schedule: List[Match] = self.prepare_schedule()
        self.team_initials = [team_initial for team_name, team_initial in Config.TEAMS.items()]

    @staticmethod
    def prepare_schedule():
        match_list = list()
        schedule_file = open("source/schedule.csv")
        schedule_reader = csv.DictReader(schedule_file)
        for row in schedule_reader:
            match = Match()
            match.date = datetime.strptime(row[Config.DATE], "%d/%m/%Y %H:%M").replace(tzinfo=Config.INDIA_TZ)
            match.game_week = int(row[Config.ROUND])
            match.number = int(row[Config.MATCH_NO])
            match.home_team = Config.TEAMS[row[Config.HOME_TEAM]]
            match.away_team = Config.TEAMS[row[Config.AWAY_TEAM]]
            match.teams = [match.home_team, match.away_team]
            match.unique_id = row[Config.UNIQUE_ID]
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
        if Config.GAME_WEEK_START < date <= Config.GAME_WEEK_2_CUT_OFF:
            return 1
        if Config.GAME_WEEK_9_CUT_OFF < date <= Config.GAME_WEEK_10_CUT_OFF:
            return 9
        if date > Config.GAME_WEEK_10_CUT_OFF:
            return 10
        game_week_start = Config.GAME_WEEK_2_CUT_OFF
        for game_week in range(2, self.max_game_week + 1):
            if game_week_start <= date < game_week_start + timedelta(days=7):
                return game_week
            game_week_start += timedelta(days=7)
        return self.max_game_week + 1

    @staticmethod
    def get_cut_off(game_week: int) -> datetime:
        if game_week <= 1:
            return Config.GAME_WEEK_START
        if game_week == 9:
            return Config.GAME_WEEK_9_CUT_OFF
        if game_week == 10:
            return Config.GAME_WEEK_10_CUT_OFF
        if game_week > 10:
            return Config.GAME_WEEK_10_CUT_OFF + timedelta(days=7)
        return Config.GAME_WEEK_2_CUT_OFF + timedelta(days=7 * (game_week - 2))

    def get_matches_being_played(self) -> List[Match]:
        return [match for match in self.schedule if match.date <= today() <= match.date + timedelta(hours=5)]

    def get_matches(self, team: str, game_week: int) -> List[Match]:
        return [match for match in self.schedule if game_week == match.game_week and team in match.teams]

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
