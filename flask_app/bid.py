import random
from typing import List, Optional, Tuple

from firestore_ci.firestore_ci import FirestoreDocument
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField, BooleanField
from wtforms.validators import NumberRange, DataRequired, ValidationError
from wtforms.widgets import Input

from config import Config
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
    def submit_bid(cls, user: User, player: Player, amount: int, auto: bool = False):
        if not 20 <= amount <= 2000:
            raise ValueError
        bid = cls._bid_instance(user, player)
        bid.amount = amount
        bid.status = 'auto bid' if auto else 'bid'
        bid.create()

    @classmethod
    def pass_bid(cls, user: User, player: Player):
        bid = cls._bid_instance(user, player)
        bid.status = 'passed'
        bid.create()

    @classmethod
    def submit_auto_bids(cls, player: Player, user: User = None) -> bool:
        users = User.objects.get() if not user else [user]
        for user in users:
            if user.balance < player.base:
                bid = cls._bid_instance(user, player)
                bid.status = 'no balance'
                bid.create()
            elif user.auto_bid:
                min_bid = player.get_min_bid(user)
                max_bid = player.get_max_bid(user)
                bid_amount = random.randrange(min_bid, max_bid + 1, 20)
                cls.submit_bid(user, player, bid_amount, auto=True)
        return cls.decide_winner(player)

    @classmethod
    def get_pending_bidders(cls, player: Player) -> List[str]:
        bids: List[Bid] = cls.objects.filter_by(player_name=player.name).get()
        return [username for username in Config.USER_LIST
                if username.lower() not in [bid.username for bid in bids]]

    @classmethod
    def decide_winner(cls, player: Player) -> bool:
        bids: List[Bid] = cls.objects.filter_by(player_name=player.name).get()
        if len(bids) != Config.USER_COUNT:
            return False
        if any(bid.winner for bid in bids):
            if player.owner:
                return False
            winning_bid = next(bid for bid in bids if bid.winner)
            player.purchase(winning_bid.username, winning_bid.amount)
            return True
        max_bid = max(bids, key=lambda bid: bid.amount)
        if not max_bid.amount:
            player.pass_player()
            return True
        max_bids = [bid for bid in bids if bid.amount == max_bid.amount]
        winning_bid: Bid = random.choice(max_bids)
        winning_bid.winner = True
        winning_bid.save()
        player.purchase(winning_bid.username, winning_bid.amount)
        return True

    @classmethod
    def remove_incomplete_bids(cls, bids: List['Bid'], bid_order: int) -> List['Bid']:
        if sum(1 for bid in bids if bid.bid_order == bid_order) < Config.USER_COUNT:
            return [bid for bid in bids if bid.bid_order != bid_order]
        return bids

    @classmethod
    def bid_list(cls, limit: int = 0) -> List['Bid']:
        if limit:
            limit += 1
            limit *= Config.USER_COUNT
            bids = cls.objects.order_by('bid_order', cls.objects.ORDER_DESCENDING).limit(limit).get()
        else:
            bids = cls.objects.order_by('bid_order', cls.objects.ORDER_DESCENDING).get()
        if not bids:
            return list()
        last_bid = max(bids, key=lambda bid: bid.bid_order)
        bids = cls.remove_incomplete_bids(bids, last_bid.bid_order)
        oldest_bid = min(bids, key=lambda bid: bid.bid_order)
        bids = cls.remove_incomplete_bids(bids, oldest_bid.bid_order)
        bids.sort(key=lambda bid: (-bid.bid_order, bid.username))
        return bids

    @classmethod
    def turn_on(cls):
        for user in User.objects.get():
            user.bidding = True
            user.save()
        return

    @classmethod
    def turn_off(cls):
        for user in User.objects.get():
            user.bidding = False
            user.save()
        return

    @classmethod
    def bid_status(cls) -> Tuple[str, Optional[Player]]:
        if not current_user.bidding:
            return 'Auction is OFF', None
        player = Player.player_in_auction()
        if not player:
            player = Player.auction_next_player()
            if not player:
                current_user.bidding = False
                current_user.save()
                return 'Auction completed', None
            cls.submit_auto_bids(player)
        else:
            cls.decide_winner(player)
        return str(), player


Bid.init()


class BidForm(FlaskForm):
    amount = IntegerField('Enter your bid', validators=[DataRequired(), NumberRange(min=20, max=2000)],
                          widget=Input(input_type='number'))
    pass_bid = BooleanField('Check here to pass the player')
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


class AutoBidForm(FlaskForm):
    auto_bid = BooleanField('Check here if you want to turn ON auto bid bot')
    submit = SubmitField('Submit')
