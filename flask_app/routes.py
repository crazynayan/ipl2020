from urllib.parse import unquote

from flask import render_template, Response, flash, redirect, url_for, request
from flask_login import login_required, current_user
from werkzeug.datastructures import MultiDict

from flask_app import ipl_app
from flask_app.bid import BidForm, Bid
from flask_app.player import Player
from flask_app.user import User


@ipl_app.route('/')
@ipl_app.route('/home')
@ipl_app.route('/users')
@login_required
def home() -> Response:
    users = User.objects.get()
    users.sort(key=lambda user_item: -user_item.points)
    return render_template('user_list.html', title='Super Fantasy League - IPL 2020', users=users)


@ipl_app.route('/users/<username>/players')
@login_required
def user_players(username: str) -> Response:
    players = Player.objects.filter_by(owner=username).get()
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('player_list.html', username=username, players=players,
                           title=f'{username.upper()} - Players')


@ipl_app.route('/players')
@login_required
def all_players() -> Response:
    players = Player.objects.get()
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('player_list.html', username=None, players=players, title=f'IPL 2020 - Players')


@ipl_app.route('/bids')
@login_required
def view_bids():
    return render_template('bid_list.html', bids=Bid.bid_list(10), users=sorted(ipl_app.config['USER_LIST']),
                           all=False, title=f'IPL 2020 - Bids')


@ipl_app.route('/bids/all')
@login_required
def view_all_bids():
    return render_template('bid_list.html', bids=Bid.bid_list(), users=sorted(ipl_app.config['USER_LIST']),
                           all=True, title=f'IPL 2020 - Bids')


@ipl_app.route('/players/<string:player_id>')
@login_required
def view_player(player_id: str):
    player = Player.get_by_id(player_id)
    if not player:
        flash("Player not found")
        return redirect(url_for('all_players'))
    bids = Bid.objects.filter_by(player_name=player.name).get()
    if len(bids) != ipl_app.config['USER_COUNT']:
        bids = list()
    bids.sort(key=lambda bid: -bid.amount)
    return render_template('profile.html', player=player, bids=bids)


@ipl_app.route('/players/name/<string:player_name>')
@login_required
def view_player_by_name(player_name: str):
    player = Player.objects.filter_by(name=unquote(player_name)).first()
    if not player:
        flash("Player not found")
        return redirect(url_for('all_players'))
    return redirect(url_for('view_player', player_id=player.id))


@ipl_app.route('/bids/submit')
@login_required
def submit_bid():
    if not current_user.bidding:
        flash('Auction is OFF. Please contact admin to turn it ON.')
        return redirect(url_for('home'))
    player = Player.player_in_auction()
    if not player:
        player = Player.auction_next_player()
        if not player:
            flash('Auction completed - Thank You')
            return redirect(url_for('home'))
        Bid.submit_auto_bids(player)
    return redirect(url_for('bid_player', player_id=player.id))


@ipl_app.route('/players/<string:player_id>/bids', methods=['GET', 'POST'])
@login_required
def bid_player(player_id: str):
    if not current_user.bidding:
        flash('Auction is OFF. Please contact admin to turn it ON.')
        return redirect(url_for('home'))
    player = Player.get_by_id(player_id)
    if not player:
        flash("Player not found")
        return redirect(url_for('home'))
    bid = Bid.objects.filter_by(player_name=player.name, username=current_user.username).first()
    if bid:
        return render_template('bid_player.html', player=player, bid=bid, form=None)
    form = BidForm(current_user.balance, player.base)
    if request.method == 'GET':
        form_data = form.data
        form_data['amount'] = player.base
        form = BidForm(current_user.balance, player.base, formdata=MultiDict(form_data))
    if not form.validate_on_submit():
        return render_template('bid_player.html', player=player, bid=None, form=form)
    Bid.submit_bid(current_user, player, form.amount.data)
    Bid.decide_winner(player)
    return redirect(url_for('submit_bid'))
