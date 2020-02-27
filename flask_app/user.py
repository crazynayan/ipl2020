from typing import Optional

from firestore_ci.firestore_ci import FirestoreDocument
from flask import flash, redirect, url_for, render_template, request
from flask_login import UserMixin, current_user, login_user, logout_user
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.urls import url_parse
from wtforms import PasswordField, SubmitField, StringField
from wtforms.validators import DataRequired

from config import Config
from flask_app import ipl_app, login


class User(FirestoreDocument, UserMixin):

    def __init__(self):
        super().__init__()
        self.username: str = str()
        self.password_hash: str = str()
        self.name: str = str()
        self.balance: int = Config.BALANCE
        self.points: float = 0.0
        self.player_count: int = 0
        self.auto_bid: bool = False
        self.bidding: bool = False

    def __repr__(self) -> str:
        return f"{self.username.upper()}"

    def set_password(self, password) -> None:
        self.password_hash = generate_password_hash(password)
        self.save()

    def check_password(self, password) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return self.username


User.init()


@login.user_loader
def load_user(username: str) -> Optional[User]:
    user = User.objects.filter_by(username=username).first()
    return user


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


@ipl_app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if not form.validate_on_submit():
        return render_template('form_template.html', title='IPL 2020 - Sign In', form=form)
    user = User.objects.filter_by(username=form.username.data).first()
    if not user or not user.check_password(form.password.data):
        flash(f"Invalid email or password.")
        return redirect(url_for('login'))
    login_user(user=user)
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).netloc != '':
        next_page = url_for('home')
    return redirect(next_page)


@ipl_app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
