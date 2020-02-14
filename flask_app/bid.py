import random
from typing import List

from firestore_ci import FirestoreDocument
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import NumberRange, DataRequired, ValidationError
from wtforms.widgets import Input

from flask_app import ipl_app
from flask_app.player import Player
from flask_app.user import User


class Bid(FirestoreDocument):

    def __init__(self):
        super().__init__()
        self.username: str = str()
        self.amount: int = 0
        self.player_name: str = str()
        self.status: str = str()
        self.bid_order: int = 0
        self.winner: bool = False

    def __repr__(self):
        return f"{self.player_name}:{self.username}:{self.amount}:{self.status}"

    @classmethod
    def _bid_instance(cls, user: User, player: Player, ) -> 'Bid':
        bid = cls()
        bid.username = user.username
        bid.player_name = player.name
        bid.bid_order = player.bid_order
        return bid

    @classmethod
    def submit_bid(cls, user: User, player: Player, amount: int):
        if not 20 <= amount <= 2000:
            raise ValueError
        bid = cls._bid_instance(user, player)
        bid.amount = amount
        bid.status = 'Submit'
        bid.create()

    @classmethod
    def pass_bid(cls, user: User, player: Player):
        bid = cls._bid_instance(user, player)
        bid.status = 'Pass'
        bid.create()

    @classmethod
    def submit_auto_bids(cls, player: Player):
        users = User.objects.get()
        for user in users:
            if user.balance < player.base:
                bid = cls._bid_instance(user, player)
                bid.status = 'No Balance'
                bid.create()
            elif user.auto_bid:
                min_sbp = min(player.sbp_2019, player.sbp_cost) if player.ipl2019_score else player.base
                min_bid = max(min(min_sbp, user.balance), player.base)
                min_bid += 20 - min_bid % 20 if min_bid % 20 else 0
                if user.balance < min_bid:
                    min_bid = user.balance
                max_sbp = max(player.sbp_2019, player.sbp_cost) if player.ipl2019_score else player.sbp_cost
                max_bid = min(max_sbp, user.balance)
                max_bid = min_bid if max_bid < min_bid else max_bid
                bid_amount = random.randrange(min_bid, max_bid + 1, 20)
                cls.submit_bid(user, player, bid_amount)
        cls.decide_winner(player)
        return

    @classmethod
    def get_pending_bidders(cls, player: Player) -> List[str]:
        # TODO Optimize it later by reading the game object. Do NOT optimize if the number of reads as less
        bids: List[Bid] = cls.objects.filter_by(player_name=player.name).get()
        return [username for username in ipl_app.config['USER_LIST'] if username not in [bid.username for bid in bids]]

    @classmethod
    def decide_winner(cls, player: Player) -> bool:
        bids: List[Bid] = cls.objects.filter_by(player_name=player.name).get()
        if len(bids) != ipl_app.config['USER_COUNT']:
            return False
        max_bid = max(bids, key=lambda bid: bid.amount)
        if not max_bid.amount:
            player.pass_player()
            return True
        max_bids = [bid for bid in bids if bid.amount == max_bid.amount]
        winning_bid: Bid = random.choice(max_bids)
        winning_bid.winner = True
        winning_bid.save()
        winner = User.objects.filter_by(username=winning_bid.username).first()
        player.purchase(winner, winning_bid.amount)
        return True

    @classmethod
    def remove_incomplete_bids(cls, bids: List['Bid'], bid_order: int) -> List['Bid']:
        if sum(1 for bid in bids if bid.bid_order == bid_order) < ipl_app.config['USER_COUNT']:
            return [bid for bid in bids if bid.bid_order != bid_order]
        return bids

    @classmethod
    def bid_list(cls, limit: int = 0) -> List['Bid']:
        if limit:
            limit += 1
            limit *= ipl_app.config['USER_COUNT']
            bids = cls.objects.order_by('bid_order', cls.objects.ORDER_DESCENDING).limit(limit).get()
        else:
            bids = cls.objects.order_by('bid_order', cls.objects.ORDER_DESCENDING).get()
        last_bid = max(bids, key=lambda bid: bid.bid_order)
        bids = cls.remove_incomplete_bids(bids, last_bid.bid_order)
        oldest_bid = min(bids, key=lambda bid: bid.bid_order)
        bids = cls.remove_incomplete_bids(bids, oldest_bid.bid_order)
        bids.sort(key=lambda bid: (-bid.bid_order, bid.username))
        return bids


Bid.init()


class BidForm(FlaskForm):
    amount = IntegerField('Enter your bid', validators=[DataRequired(), NumberRange(min=20, max=2000)],
                          widget=Input(input_type='number'))
    submit = SubmitField('Submit')

    def __init__(self, balance, base, *args, **kwargs):
        self.balance = balance
        self.base = base
        super().__init__(*args, **kwargs)

    def validate_amount(self, amount: IntegerField):
        if not isinstance(amount.data, int):
            return
        if amount.data % 5 != 0:
            raise ValidationError('Bids should be in multiple of 5')
        if amount.data > self.balance:
            raise ValidationError('You cannot bid more than your balance')
        if amount.data < self.base:
            raise ValidationError('You cannot bid less than the player base price')
