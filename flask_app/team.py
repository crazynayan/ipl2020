from typing import List, Optional

from firestore_ci.firestore_ci import FirestoreDocument
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, ValidationError

from config import Config
from flask_app.bid import Bid
from flask_app.player import Player
from flask_app.schedule import schedule


class UserTeam(FirestoreDocument):
    NORMAL = "Normal"
    CAPTAIN = "Captain"
    SUB = "Sub"
    MULTIPLIER = {NORMAL: 1.0, CAPTAIN: 2.0, SUB: 0.5}

    def __init__(self):
        super().__init__()
        self.game_week: int = 0
        self.player_name: str = str()
        self.owner: str = str()
        self.type: str = self.NORMAL
        self.final_score: float = 0.0
        self.matches: List[dict] = list()
        self.team: str = str()
        self.group: int = 0

    def __repr__(self):
        return f"GW-{self.game_week}:{self.player_name}:{self.type}:{self.final_score}:M-{len(self.matches)}"

    @classmethod
    def last_game_week(cls) -> int:
        last_team: UserTeam = cls.objects.order_by("game_week", cls.objects.ORDER_DESCENDING).first()
        return last_team.game_week if last_team else 0

    @classmethod
    def last_locked_game_week(cls) -> int:
        last_game_week = cls.last_game_week()
        if not last_game_week:
            return 0
        return last_game_week - 1 if last_game_week > schedule.get_game_week() else last_game_week

    @classmethod
    def create_game_week(cls) -> str:
        last_bid = Bid.objects.order_by("bid_order", Bid.objects.ORDER_DESCENDING).first()
        if not last_bid or last_bid.bid_order != Config.TOTAL_PLAYERS:
            return "Auction is incomplete"
        last_game_week = cls.last_game_week()
        if last_game_week and not schedule.can_create_game_week(last_game_week):
            return f"Gameweek {last_game_week} already created."
        last_user_team = cls.objects.filter_by(game_week=last_game_week).get() if last_game_week else None
        players = Player.objects.get()
        next_game_week = last_game_week + 1
        user_teams: List[dict] = list()
        for index, player in enumerate(players):
            user_team = cls()
            user_team.game_week = next_game_week
            user_team.player_name = player.name
            user_team.owner = player.owner
            user_team.team = player.team
            if last_user_team:
                last_player = next(team for team in last_user_team if team.player_name == user_team.player_name)
                user_team.type = last_player.type
                user_team.group = last_player.group
                user_team.final_score = last_player.final_score
            user_team.matches = [{"match": match, "score": 0.0}
                                 for match in schedule.get_matches(player.team, next_game_week)]
            user_teams.append(cls.objects.to_dicts([user_team])[0])
            if (index + 1) % 10 == 0:
                print(f"Gameweek {next_game_week}: {index + 1} player of {len(players)} created")
        cls.objects.create_all(user_teams)
        print(f"Gameweek {next_game_week} created")
        return str()

    @classmethod
    def get_dummy_user_team(cls, game_week: int, team: str) -> "UserTeam":
        user_team = UserTeam()
        user_team.game_week = game_week
        user_team.matches = [{"match": match, "score": 0.0} for match in schedule.get_matches(team, game_week)]
        return user_team

    @property
    def list_group_item(self) -> str:
        return "list-group-item-success" if self.type == self.CAPTAIN else "list-group-item-danger" \
            if self.type == self.SUB else str()

    @classmethod
    def get_players_by_game_week(cls, owner: str, game_week: int) -> List["UserTeam"]:
        return cls.objects.filter_by(owner=owner, game_week=game_week).get()

    @classmethod
    def get_last_match_played(cls, player) -> Optional["UserTeam"]:
        game_week = schedule.get_game_week_last_match_played(player.team)
        if not game_week:
            return None
        return cls.objects.filter_by(player_name=player.name, game_week=game_week).first()

    def update_score(self, player: Player, delta_score: float) -> bool:
        score_updated = False
        for match in reversed(self.matches):
            if schedule.match_played(match["match"].split()[0], player.team):
                match["score"] += delta_score * self.MULTIPLIER[self.type]
                score_updated = True
                break
        if score_updated:
            self.final_score += delta_score * self.MULTIPLIER[self.type]
        return score_updated


UserTeam.init("user_teams")


class MakeCaptainForm(FlaskForm):
    captain = SelectField("Select Captain")
    sub1 = SelectField("Select Sub 1")
    sub2 = SelectField("Select Sub 2")
    submit = SubmitField("Save")

    def validate_captain(self, captain: SelectField):
        if captain.data == self.sub1.data or captain.data == self.sub2.data:
            raise ValidationError("You cannot select the same player for captain and sub")

    def validate_sub2(self, sub2: SelectField):
        if sub2.data == self.sub1.data:
            raise ValidationError("You cannot select the same player for both the sub")
