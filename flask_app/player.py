import random
from typing import Optional, List, Tuple

from firestore_ci import FirestoreDocument

from flask_app import ipl_app
from flask_app.schedule import schedule
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
        self.bid_order: int = 0
        self._sbp_cost: int = 0

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
        if self._sbp_cost:
            return self._sbp_cost
        balance = sum([user.balance for user in User.objects.get()])
        if balance == ipl_app.config['BALANCE'] * ipl_app.config['USER_COUNT']:
            total_cost = ipl_app.config['TOTAL_COST']
        else:
            total_cost = sum(player.cost for player in self.objects.filter_by(auction_status=str()).get())
            total_cost += self.cost
        sbp_cost = int(round(balance * self.cost / total_cost, -1))
        if self.auction_status == 'bidding':
            self._sbp_cost = sbp_cost
            self.save()
        return sbp_cost

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
        player.bid_order = ipl_app.config['TOTAL_PLAYERS'] - len(players) + 1
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

    def get_schedule_by_game_week(self) -> List[Tuple[int, List[str]]]:
        return [(game_week, schedule.get_matches(self.team, game_week))
                for game_week in range(1, schedule.max_game_week + 1)]

    def get_min_bid(self, user: User = None) -> int:
        min_sbp = min(self.sbp_2019, self.sbp_cost) if self.ipl2019_score else self.base
        min_bid = max(min(min_sbp, user.balance) if user else min_sbp, self.base)
        min_bid += 20 - min_bid % 20 if min_bid % 20 else 0
        if user and user.balance < min_bid:
            min_bid = user.balance
        return min_bid

    def get_max_bid(self, user: User = None) -> int:
        max_sbp = max(self.sbp_2019, self.sbp_cost) if self.ipl2019_score else self.sbp_cost
        max_bid = min(max_sbp, user.balance) if user else max_sbp
        min_bid = self.get_min_bid(user)
        max_bid = min_bid if max_bid < min_bid else max_bid
        return max_bid


Player.init()
