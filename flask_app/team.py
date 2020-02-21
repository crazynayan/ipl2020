from datetime import datetime
from typing import List

from firestore_ci import FirestoreDocument

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
        self.type: str = str()
        self.final_score: float = 0.0
        self.matches: List[dict] = list()
        self.team: str = str()
        self.group: int = 0

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
            user_team.type = cls.NORMAL
            user_team.matches = [{'match': match, 'score': 0.0} for match in
                                 schedule.get_matches(player.team, next_game_week)]
            user_team.create()
        return str()


UserTeam.init('user_teams')
