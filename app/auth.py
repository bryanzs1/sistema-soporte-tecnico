from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, login_required, current_user
import os

from app import db, login, translate, limiter
from app.models import User
from app.forms import LoginForm, ForcePasswordChangeForm


# flask-login expects a user loader callback
@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

bp = Blueprint('auth', __name__)


def _t(text):
    return translate(text, session.get('lang', 'en'))


def must_change_default_admin_password(user):
    default_admin_username = os.environ.get('DEFAULT_ADMIN_USERNAME', 'admin')
    default_admin_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
    return (
        user.is_authenticated
        and user.is_admin()
        and user.username == default_admin_username
        and user.check_password(default_admin_password)
    )


@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
@limiter.limit("5 per 15 minutes")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_t('Invalid username or password'), 'danger')
            return redirect(url_for('auth.login'))
        if not user.is_active:
            flash(_t('This account has been deactivated. Please contact an administrator.'), 'danger')
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        if must_change_default_admin_password(user):
            flash(_t('Please change the default admin password before continuing'), 'warning')
            return redirect(url_for('auth.force_password_change'))
        flash(_t('Welcome back, {username}!').format(username=user.username), 'success')
        return redirect(url_for('main.index'))
    return render_template('auth/login.html', form=form)


@bp.route('/force-password-change', methods=['GET', 'POST'], endpoint='force_password_change')
@login_required
def force_password_change():
    if not must_change_default_admin_password(current_user):
        return redirect(url_for('main.index'))

    form = ForcePasswordChangeForm()
    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash(_t('Password updated successfully'), 'success')
        return redirect(url_for('main.index'))

    return render_template('auth/force_password_change.html', form=form)


@bp.route('/logout', endpoint='logout')
def logout():
    logout_user()
    flash(_t('You have been logged out successfully'), 'info')
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    # registration disabled; only administrators may add accounts via admin panel
    abort(404)
