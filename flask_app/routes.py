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
    users = User.objects.get()
    users.sort(key=lambda user_item: -user_item.points)
    return render_template('user_list.html', title='Super Fantasy League - IPL 2020', users=users)


@ipl_app.route('/users/<username>/players')
@login_required
def user_players(username: str) -> Response:
    players = Player.objects.filter_by(owner=username).get()
    players.sort(key=lambda player: -player.score)
    return render_template('user_players.html', username=username, players=players, title='IPL 2020 - Players')


@ipl_app.route('/players/top50')
@login_required
def top50_players() -> Response:
    players = Player.objects.order_by('score', Player.objects.ORDER_DESCENDING).limit(50).get()
    return render_template('player_list.html', players=players, title='IPL 2020 - Top 50')


@ipl_app.route('/teams/<team>/players')
@login_required
def team_players(team: str) -> Response:
    players = Player.objects.filter_by(team=team).get()
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('player_list.html', players=players, title=f'IPL 2020 - {team} Players')


@ipl_app.route('/unsold/players')
@login_required
def unsold_players() -> Response:
    players = Player.objects.filter_by(owner=None).get()
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('user_players.html', username='Unsold', players=players, title=f'IPL 2020 - Unsold Players')


@ipl_app.route('/bids')
@login_required
def view_bids():
    return render_template('bid_list.html', players=list(), title=f'IPL 2020 - Bids')
