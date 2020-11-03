from typing import Tuple
from urllib.parse import unquote

from flask import render_template, Response, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from werkzeug.datastructures import MultiDict

from config import Config
from flask_app import ipl_app
from flask_app.bid import BidForm, Bid, AutoBidForm
from flask_app.match_score import MatchPlayer
from flask_app.player import Player
from flask_app.schedule import schedule
from flask_app.team import UserTeam, MakeCaptainForm
from flask_app.user import User


@ipl_app.route("/")
@ipl_app.route("/home")
@ipl_app.route("/users")
@login_required
def home() -> Response:
    users = User.objects.get()
    users.sort(key=lambda user_item: -user_item.points)
    return render_template("user_list.html", title="Super Fantasy League - IPL 2020", users=users)


@ipl_app.route("/users/<username>/players")
@login_required
def user_players(username: str) -> Response:
    players = Player.objects.filter_by(owner=username).get()
    players.sort(key=lambda player: (-player.score, -player.price))
    last_game_week = UserTeam.last_locked_game_week()
    return render_template("player_list.html", username=username, players=players, game_week=last_game_week,
                           title=f"{username.upper()} - Players")


@ipl_app.route("/players")
@login_required
def all_players() -> Response:
    players = Player.objects.get()
    players.sort(key=lambda player: (-player.score, -player.price))
    return render_template("player_list.html", username=None, players=players, title=f"IPL 2020 - Players")


@ipl_app.route("/bids")
@login_required
def view_bids():
    return render_template("bid_list.html", bids=Bid.bid_list(10), users=sorted(ipl_app.config["USER_LIST"]),
                           all=False, title=f"IPL 2020 - Bids")


@ipl_app.route("/bids/all")
@login_required
def view_all_bids():
    return render_template("bid_list.html", bids=Bid.bid_list(), users=sorted(ipl_app.config["USER_LIST"]),
                           all=True, title=f"IPL 2020 - Bids")


@ipl_app.route("/players/<string:player_id>")
@login_required
def view_player(player_id: str):
    player = Player.get_by_id(player_id)
    if not player:
        flash("Player not found")
        return redirect(url_for("all_players"))
    bids = Bid.objects.filter_by(player_name=player.name).get()
    if len(bids) != ipl_app.config["USER_COUNT"]:
        bids = list()
    bids.sort(key=lambda bid: -bid.amount)
    player_matches = UserTeam.objects.filter_by(player_name=player.name).get()
    last_locked_game_week = UserTeam.last_locked_game_week()
    player_matches = [team for team in player_matches if team.game_week <= last_locked_game_week]
    player_matches.sort(key=lambda team: team.game_week)
    from_game_week = player_matches[-1].game_week + 1 if player_matches else 1
    final_score = player_matches[-1].final_score if player_matches else 0
    for game_week in range(from_game_week, schedule.max_game_week + 1):
        player_matches.append(UserTeam.get_dummy_user_team(game_week, player.team))
    return render_template("profile.html", player=player, bids=bids, schedule=player_matches, final_score=final_score)


@ipl_app.route("/players/name/<string:player_name>")
@login_required
def view_player_by_name(player_name: str):
    player: Player = Player.objects.filter_by(name=unquote(player_name)).first()
    if not player:
        flash("Player not found")
        return redirect(url_for("all_players"))
    return redirect(url_for("view_player", player_id=player.id))


@ipl_app.route("/bids/submit")
@login_required
def submit_bid():
    bid_status: Tuple[str, Player] = Bid.bid_status()
    message, player = bid_status
    if not player:
        flash(message)
        return redirect(url_for("home"))
    return redirect(url_for("bid_player", player_id=player.id))


@ipl_app.route("/players/<string:player_id>/bids", methods=["GET", "POST"])
@login_required
def bid_player(player_id: str):
    if not current_user.bidding:
        flash("Auction is OFF")
        return redirect(url_for("home"))
    player = Player.get_by_id(player_id)
    if not player:
        flash("Player not found")
        return redirect(url_for("home"))
    bid = Bid.objects.filter_by(player_name=player.name, username=current_user.username).first()
    last_player: Player = Player.objects.filter_by(
        bid_order=player.bid_order - 1).first() if player.bid_order > 1 else None
    last_bids = Bid.objects.filter_by(bid_order=last_player.bid_order).get() if last_player else list()
    last_bids.sort(key=lambda bid_item: -bid_item.amount)
    player_matches = [UserTeam.get_dummy_user_team(game_week, player.team)
                      for game_week in range(1, schedule.max_game_week + 1)]
    if bid:
        return render_template("bid_player.html", player=player, bid=bid, form=None, bids=last_bids,
                               last_player=last_player, schedule=player_matches)
    form = BidForm(current_user.balance, player.base)
    if request.method == "GET":
        form_data = form.data
        form_data["amount"] = player.base
        form = BidForm(current_user.balance, player.base, formdata=MultiDict(form_data))
    if not form.validate_on_submit():
        return render_template("bid_player.html", player=player, bid=None, form=form, bids=last_bids,
                               last_player=last_player, schedule=player_matches)
    if form.pass_bid.data:
        Bid.pass_bid(current_user, player)
    else:
        Bid.submit_bid(current_user, player, form.amount.data)
    Bid.decide_winner(player)
    return redirect(url_for("submit_bid"))


@ipl_app.route("/user_profile", methods=["POST", "GET"])
@login_required
def user_profile():
    form = AutoBidForm()
    if not form.validate_on_submit():
        return render_template("form_template.html", form=form)
    if current_user.auto_bid != form.auto_bid.data:
        current_user.auto_bid = form.auto_bid.data
        current_user.save()
    if current_user.auto_bid:
        player = Player.player_in_auction()
        if player and not Bid.objects.filter_by(player_name=player.name, username=current_user.username).first():
            Bid.submit_auto_bids(player, current_user)
    return redirect(url_for("submit_bid"))


@ipl_app.route("/current_bid_status")
@login_required
def current_bid_status():
    message, player = Bid.bid_status()
    if not player:
        return jsonify(message=message)
    pending_bidders = Bid.get_pending_bidders(player)
    player_tag = f"{player.bid_order} - {player.name} -"
    if not pending_bidders:
        return jsonify(message=f"{player_tag} Bidding complete")
    if len(pending_bidders) <= 5:
        pending_bidders.sort()
        user_list = " ".join(pending_bidders)
        return jsonify(message=f"{player_tag} Awaiting bids from {user_list}")
    return jsonify(message=f"{player_tag} Awaiting bids from {len(pending_bidders)} users")


@ipl_app.route("/user_teams/<string:owner>/gameweek/<int:game_week>")
@login_required
def user_team(owner: str, game_week: int):
    if not 0 < game_week <= schedule.get_game_week():
        flash("Invalid Gameweek")
        return redirect(url_for("my_team"))
    return view_team(owner, game_week, edit=False)


@ipl_app.route("/my_team")
@login_required
def my_team():
    return view_team(current_user.username, schedule.get_game_week() + 1, edit=True)


def view_team(owner: str, game_week: int, edit: bool) -> Response:
    players = UserTeam.get_players_by_game_week(owner, game_week)
    captains = sum(1 for player in players if player.type == Config.CAPTAIN)
    cut_off = schedule.get_cut_off(game_week).strftime("%a %d %b %H:%M")
    max_captains = len(players) // 3
    groups = [player for player in players if player.group > 0]
    groups.sort(key=lambda player_item: (player_item.group, player_item.type, -player_item.final_score))
    players = [player for player in players if player.group == 0]
    players.sort(key=lambda player_item: -player_item.final_score)
    last_game_week = UserTeam.last_locked_game_week()
    return render_template("user_team.html", players=players, cut_off=cut_off, groups=groups, captains=captains,
                           game_week=game_week, max_captains=max_captains, title=f"{owner.upper()} Team", edit=edit,
                           owner=owner, all_game_weeks=last_game_week)


@ipl_app.route("/my_team/make_captain", methods=["GET", "POST"])
@login_required
def make_captain():
    current_game_week = schedule.get_game_week()
    players = UserTeam.get_players_by_game_week(current_user.username, current_game_week + 1)
    players.sort(key=lambda player_item: -player_item.final_score)
    number_of_captains = sum(1 for player in players if player.type == Config.CAPTAIN)
    if len(players) // 3 == number_of_captains:
        flash("You already have maximum captains selected. Please remove a group to appoint more captains.")
        return redirect(url_for("my_team"))
    form = MakeCaptainForm()
    form.captain.choices = [(p.player_name, f"{p.player_name} (M-{len(p.matches)}, P-{p.final_score})")
                            for p in players if p.type == Config.NORMAL]
    if current_game_week > 1:
        players.sort(key=lambda player_item: player_item.final_score)
        form.sub1.choices = [(p.player_name, f"{p.player_name} (M-{len(p.matches)}, P-{p.final_score})")
                             for p in players if p.type == Config.NORMAL]
    else:
        form.sub1.choices = form.captain.choices[1:]
        form.sub1.choices.append(form.captain.choices[0])
    form.sub2.choices = form.sub1.choices[:]
    form.sub2.choices[0], form.sub2.choices[1] = form.sub2.choices[1], form.sub2.choices[0]
    if not form.validate_on_submit():
        return render_template("form_template.html", title=f"Make Captain for GW-{current_game_week + 1}", form=form)
    group = number_of_captains + 1
    captain = next(player for player in players if player.player_name == form.captain.data)
    captain.group = group
    captain.type = Config.CAPTAIN
    captain.save()
    sub1 = next(player for player in players if player.player_name == form.sub1.data)
    sub1.group = group
    sub1.type = Config.SUB
    sub1.save()
    sub2 = next(player for player in players if player.player_name == form.sub2.data)
    sub2.group = group
    sub2.type = Config.SUB
    sub2.save()
    return redirect(url_for("my_team"))


@ipl_app.route("/my_team/remove_group/<int:group>/captain/<string:captain>")
@login_required
def remove_group(group: int, captain: str):
    players = UserTeam.get_players_by_game_week(current_user.username, schedule.get_game_week() + 1)
    group_players = [player for player in players if player.group == group]
    if not group_players or not any(player.player_name == captain for player in group_players):
        flash("Error in removing group")
        return redirect(url_for("my_team"))
    for player in group_players:
        player.group = 0
        player.type = Config.NORMAL
        player.save()
    for player in players:
        if player.group <= group:
            continue
        player.group -= 1
        player.save()
    return redirect((url_for("my_team")))


@ipl_app.route("/schedule")
@login_required
def view_schedule():
    return render_template("schedule.html", schedule=schedule.schedule)


@ipl_app.route("/schedule/<string:match_id>/match_score")
@login_required
def view_match_score(match_id: str):
    players = MatchPlayer.objects.filter_by(match_id=match_id).get()
    players.sort(key=lambda player: -player.adjusted_points)
    return render_template("match_score.html", players=players, title="Schedule")


@ipl_app.route("/man_of_the_match")
@login_required
def view_man_of_the_match():
    players = MatchPlayer.objects.filter_by(man_of_the_match=True).get()
    for player in players:
        player.match_number = next(match.number for match in schedule.schedule if match.unique_id == player.match_id)
    return render_template("man_of_the_match.html", players=players, title="Man of the match")
