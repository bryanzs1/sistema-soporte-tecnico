from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db, login, translate
from app.models import User
from app.forms import LoginForm


# flask-login expects a user loader callback
@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

bp = Blueprint('auth', __name__)


def _t(text):
    return translate(text, session.get('lang', 'en'))


@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    # debug entry
    print('auth.login called, method=', request.method)
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_t('Invalid username or password'), 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        flash(_t('Welcome back, {username}!').format(username=user.username), 'success')
        return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form)


@bp.route('/logout', endpoint='logout')
def logout():
    logout_user()
    flash(_t('You have been logged out successfully'), 'info')
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    # registration disabled; only administrators may add accounts via admin panel
    abort(404)
