from datetime import datetime
from typing import List

from firestore_ci import FirestoreDocument
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, ValidationError

from flask_app import ipl_app
from flask_app.bid import Bid
from flask_app.player import Player
from flask_app.schedule import schedule


class UserTeam(FirestoreDocument):
    NORMAL = 'Normal'
    CAPTAIN = 'Captain'
    SUB = 'Sub'

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
    def create_game_week(cls, date: datetime = None) -> str:
        date = datetime.utcnow() if not date else date
        if not ipl_app.config['AUCTION_COMPLETE']:
            last_bid = Bid.objects.order_by('bid_order', Bid.objects.ORDER_DESCENDING).first()
            if not last_bid or last_bid.bid_order != ipl_app.config['TOTAL_PLAYERS']:
                return 'Auction is incomplete'
            ipl_app.config['AUCTION_COMPLETE'] = True
        last_team = cls.objects.order_by('game_week', Bid.objects.ORDER_DESCENDING).first()
        current_game_week = last_team.game_week if last_team else 0
        if current_game_week and date < schedule.get_cut_off(current_game_week):
            return f'GW-{current_game_week} already created.'
        players = Player.objects.filter('owner', '>', str()).get()
        next_game_week = current_game_week + 1
        for player in players:
            user_team = cls()
            user_team.game_week = next_game_week
            user_team.player_name = player.name
            user_team.owner = player.owner
            user_team.team = player.team
            if current_game_week > 1:
                previous_game_week = cls.objects.filter_by(player_name=player.name, game_week=current_game_week).first()
                user_team.type = previous_game_week.type
                user_team.final_score = previous_game_week.final_score
            user_team.matches = [{'match': match, 'score': 0.0} for match in
                                 schedule.get_matches(player.team, next_game_week)]
            user_team.create()
        return str()

    @property
    def list_group_item(self):
        return 'list-group-item-success' if self.type == self.CAPTAIN else 'list-group-item-danger' \
            if self.type == self.SUB else str()

    @classmethod
    def get_players_next_game_week(cls, owner: str) -> List['UserTeam']:
        next_game_week = schedule.get_game_week() + 1
        return UserTeam.objects.filter_by(owner=owner, game_week=next_game_week).get()


UserTeam.init('user_teams')


class MakeCaptainForm(FlaskForm):
    captain = SelectField('Select Captain')
    sub1 = SelectField('Select Sub 1')
    sub2 = SelectField('Select Sub 2')
    submit = SubmitField('Save')

    def validate_captain(self, captain: SelectField):
        if captain.data == self.sub1.data or captain.data == self.sub2.data:
            raise ValidationError('You cannot select the same player for captain and sub')

    def validate_sub1(self, sub1: SelectField):
        if sub1.data == self.sub2.data:
            raise ValidationError('You cannot select the same player for both the sub')
