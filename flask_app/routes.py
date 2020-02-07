from copy import deepcopy

from flask import render_template, Response
from flask_login import login_required

from flask_app import ipl_app
from flask_app.player import Player
from flask_app.user import User


@ipl_app.route('/')
@ipl_app.route('/home')
@ipl_app.route('/users')
@login_required
def home() -> Response:
    users = User.objects.filter('points', '>', 0).get()
    users.sort(key=lambda user_item: -user_item.points)
    return render_template('user_list.html', title='Super Fantasy League - IPL 2019', users=users)


@ipl_app.route('/users/<username>/players')
@login_required
def user_players(username: str) -> Response:
    players = Player.objects.filter('owners', User.objects.ARRAY_CONTAINS, username).get()
    players.sort(key=lambda player: -player.score)
    return render_template('user_players.html', username=username, players=players, title='IPL 2019 - Players')


@ipl_app.route('/players/top50')
@login_required
def top50_players() -> Response:
    players = Player.objects.order_by('score', Player.objects.ORDER_DESCENDING).limit(50).get()
    return render_template('player_list.html', players=players, title='IPL 2019 - Top 50')


@ipl_app.route('/teams/<team>/players')
@login_required
def team_players(team: str) -> Response:
    players = Player.objects.filter_by(team=team).get()
    players.sort(key=lambda player: -player.score)
    return render_template('player_list.html', players=players, title=f'IPL 2019 - {team} Players')


@ipl_app.route('/unsold/players')
@login_required
def unsold_players() -> Response:
    players = Player.objects.filter_by(owners=list()).get()
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('user_players.html', username='Unsold', players=players, title=f'IPL 2019 - Unsold Players')


@ipl_app.route('/bids')
@login_required
def view_bids():
    players = Player.objects.get()
    players = [player for player in players if (player.bids1 and player.owner1) or (player.bids2 and player.owner2)]
    users_not_participated = [user.username for user in User.objects.get()
                              if all(player.bids1[user.username] == -2 for player in players if player.bids1)]
    player_list = list()
    for player in players:
        if player.bids1 and player.bids2 and player.owner2:
            new_player = deepcopy(player)
            new_player.set_id('new')
            new_player.bids1 = dict()
        else:
            new_player = player
        if not new_player.bids1 and new_player.bids2:
            new_player.bids1 = new_player.bids2
            new_player.bid_order1 = new_player.bid_order2
            new_player.owner1 = new_player.owner2
            new_player.price1 = new_player.price2
        player.bids = [{'user': bid_user, 'amount': bid_amount} for bid_user, bid_amount in player.bids1.items()
                       if bid_user not in users_not_participated]
        player.bids.sort(key=lambda bid_item: bid_item['user'])
        if new_player != player:
            new_player.bids = [{'user': bid_user, 'amount': bid_amount}
                               for bid_user, bid_amount in new_player.bids1.items()
                               if bid_user not in users_not_participated]
            new_player.bids.sort(key=lambda bid_item: bid_item['user'])
            player_list.append(new_player)
        player_list.append(player)
    player_list.sort(key=lambda player_item: player_item.bid_order1)
    return render_template('bid_list.html', players=player_list, title=f'IPL 2019 - Bids')
