import random
from typing import Optional

from firestore_ci import FirestoreDocument

from flask_app import ipl_app
from flask_app.user import User


class Player(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.name: str = str()
        self.cost: int = 0
        self.base: int = 0
        self.country: str = str()
        self.type: str = str()
        self.ipl2019_score: float = 0.0
        self.team: str = str()
        self.score: float = 0.0
        self.ipl2019_rank: int = 0
        self.cost_rank: int = 0
        self.owner: Optional[str] = None
        self.price: int = 0
        self.auction_status: str = str()

    def __repr__(self) -> str:
        return f"{self.name}"

    @property
    def image(self) -> str:
        file_name = f"{self.name.lower().replace(' ', '_')}.jpg"
        if file_name not in ipl_app.config['IMAGES']:
            file_name = 'default.jpg'
        return f'images/{file_name}'

    @property
    def sbp_2019(self) -> int:
        return int(round(ipl_app.config['COST_2019'] * self.ipl2019_score / ipl_app.config['SCORE_2019'], -1))

    @property
    def sbp_cost(self) -> int:
        return int(round(ipl_app.config['BALANCE'] * ipl_app.config['USER_COUNT'] * self.cost
                         / ipl_app.config['TOTAL_COST'], -1))

    @property
    def cost_rank_total(self) -> int:
        return ipl_app.config['PLAYERS_COST']

    @property
    def ipl2019_rank_total(self) -> int:
        return ipl_app.config['PLAYERS_2019']

    @classmethod
    def player_in_auction(cls) -> Optional['Player']:
        return cls.objects.filter_by(auction_status='bidding').first()

    @classmethod
    def auction_next_player(cls) -> Optional['Player']:
        players = cls.objects.filter_by(auction_status=str()).get()
        if not players:
            return None
        player = random.choice(players)
        player.auction_status = 'bidding'
        player.save()
        return player

    def purchase(self, user: User, amount: int):
        if self.auction_status != 'bidding':
            return
        self.price = amount
        self.owner = user.username
        self.auction_status = 'completed'
        self.save()
        user.balance -= amount
        user.player_count += 1
        user.save()

    def pass_player(self):
        if self.auction_status != 'bidding':
            return
        self.auction_status = 'completed'
        self.save()


Player.init()
