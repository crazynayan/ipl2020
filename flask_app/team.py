from typing import List, Optional

from firestore_ci.firestore_ci import FirestoreDocument
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, ValidationError

from config import Config
from flask_app.bid import Bid
from flask_app.player import Player
from flask_app.schedule import schedule


class UserTeam(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.game_week: int = 0
        self.player_name: str = str()
        self.owner: str = str()
        self.type: str = Config.NORMAL
        self.final_score: float = 0.0
        self.matches: List[dict] = list()
        self.team: str = str()
        self.group: int = 0
        self.previous_week_score: float = 0.0

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
    def create_game_week(cls):
        last_bid = Bid.objects.order_by("bid_order", Bid.objects.ORDER_DESCENDING).first()
        if not last_bid or last_bid.bid_order != Config.TOTAL_PLAYERS:
            print("Auction is incomplete")
            return
        last_game_week = cls.last_game_week()
        if last_game_week and not schedule.can_create_game_week(last_game_week):
            print(f"Gameweek {last_game_week} already created")
            return
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
                user_team_previous_gw = next(team for team in last_user_team
                                             if team.player_name == user_team.player_name)
                user_team.type = user_team_previous_gw.type
                user_team.group = user_team_previous_gw.group
                user_team.final_score = user_team.previous_week_score = user_team_previous_gw.final_score
            user_team.matches = [{"match": match.get_text(player.team), "score": 0.0, "match_id": str(match.unique_id)}
                                 for match in schedule.get_matches(player.team, next_game_week)]
            user_teams.append(cls.objects.to_dicts([user_team])[0])
            if (index + 1) % 10 == 0:
                print(f"Gameweek {next_game_week}: {index + 1} player of {len(players)} created")
        cls.objects.create_all(user_teams)
        print(f"Gameweek {next_game_week} created")
        return

    @classmethod
    def update_matches(cls, game_week: int):
        # Update matches in UserTeam when schedule changes after the gameweek is created
        user_teams = cls.objects.filter_by(game_week=game_week).get()
        if not user_teams:
            print("No user teams created for the given game week")
            return
        updated_user_teams = list()
        for user_team in user_teams:
            matches = [{"match": match.get_text(user_team.team), "score": 0.0, "match_id": str(match.unique_id)}
                       for match in schedule.get_matches(user_team.team, game_week)]
            if user_team.matches == matches:
                continue
            # Add new matches to UserTeam
            for match in matches:
                user_team_match = next((user_team_match for user_team_match in user_team.matches
                                        if user_team_match["match"][:5] == match["match"][:5]), None)
                if not user_team_match:
                    user_team.matches.append(match)
            # Remove unnecessary matches from UserTeam and update matches in the UserTeam
            user_team_matches = list()
            for user_team_match in user_team.matches:
                match = next((match for match in matches if match["match"][:5] == user_team_match["match"][:5]), None)
                if not match:
                    continue
                user_team_match["match"] = match["match"]
                user_team_match["match_id"] = match["match_id"]
                user_team_matches.append(user_team_match)
            user_team.matches = user_team_matches
            # Update UserTeam
            updated_user_teams.append(user_team)
        if not updated_user_teams:
            print("No user teams updated")
            return
        cls.objects.save_all(updated_user_teams)
        print(f"{len(updated_user_teams)} user teams updated")
        return

    @classmethod
    def get_dummy_user_team(cls, game_week: int, team: str) -> "UserTeam":
        user_team = UserTeam()
        user_team.game_week = game_week
        user_team.matches = [{"match": match.get_text(team), "score": 0.0, "match_id": str(match.unique_id)}
                             for match in schedule.get_matches(team, game_week)]
        return user_team

    @property
    def list_group_item(self) -> str:
        return "list-group-item-success" if self.type == Config.CAPTAIN else "list-group-item-danger" \
            if self.type == Config.SUB else str()

    @classmethod
    def get_players_by_game_week(cls, owner: str, game_week: int) -> List["UserTeam"]:
        return cls.objects.filter_by(owner=owner, game_week=game_week).get()

    @classmethod
    def get_last_match_played(cls, player) -> Optional["UserTeam"]:
        game_week = schedule.get_game_week_last_match_played(player.team)
        if not game_week:
            return None
        return cls.objects.filter_by(player_name=player.name, game_week=game_week).first()

    def update_match_score(self, match_id: str, score: int):
        match = next(match for match in self.matches if match["match_id"] == match_id)
        match["score"] = float(score) * Config.MULTIPLIER[self.type]
        self.final_score = self.previous_week_score + sum(match["score"] for match in self.matches)


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
