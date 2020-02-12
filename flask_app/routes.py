from flask import render_template, Response, flash, redirect, url_for
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
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('user_players.html', username=username, players=players, title='IPL 2020 - Players')


@ipl_app.route('/players')
@login_required
def all_players() -> Response:
    players = Player.objects.get()
    players.sort(key=lambda player: (-player.score, -player.cost))
    return render_template('player_list.html', players=players, title='IPL 2020 - Players')


@ipl_app.route('/bids')
@login_required
def view_bids():
    return render_template('bid_list.html', players=list(), title=f'IPL 2020 - Bids')


@ipl_app.route('/players/<string:player_id>')
@login_required
def view_player(player_id: str):
    player = Player.get_by_id(player_id)
    if not player:
        flash("Player not found")
        return redirect(url_for('all_players'))
    return render_template('profile.html', player=player)
