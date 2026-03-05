from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session
from flask_login import login_user, logout_user, login_required, current_user
import os

from app import db, login, translate, limiter
from app.models import User
from app.forms import LoginForm, ForcePasswordChangeForm
from app.security import AuditHelper


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
        
        # Check if account is locked due to failed attempts
        if user and user.is_account_locked():
            AuditHelper.log_login_attempt(user, False)
            flash(_t('Account is locked due to multiple failed login attempts. Try again later.'), 'danger')
            return redirect(url_for('auth.login'))
        
        # Check credentials
        if user is None or not user.check_password(form.password.data):
            if user:
                user.record_failed_login()
                AuditHelper.log_login_attempt(user, False)
                if user.is_account_locked():
                    flash(_t('Account locked. Too many failed attempts.'), 'danger')
                else:
                    flash(_t('Invalid username or password'), 'danger')
            else:
                flash(_t('Invalid username or password'), 'danger')
            return redirect(url_for('auth.login'))
        
        # Check if account is active
        if not user.is_active:
            AuditHelper.log_login_attempt(user, False)
            flash(_t('This account has been deactivated. Please contact an administrator.'), 'danger')
            return redirect(url_for('auth.login'))
        
        # Successful login: reset failed attempts and log audit
        user.reset_failed_login()
        AuditHelper.log_login_attempt(user, True)
        
        # Check if 2FA is enabled
        if user.totp_enabled:
            session['totp_user_id'] = user.id
            session['totp_verified'] = False
            return redirect(url_for('auth.verify_totp'))
        
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
        # Validate password strength
        from app.security import PasswordValidator, AuditHelper
        from app.models import PasswordHistory
        
        is_valid, message = PasswordValidator.validate(form.new_password.data)
        if not is_valid:
            flash(_t('Password does not meet security requirements: ') + message, 'warning')
            return render_template('auth/force_password_change.html', form=form)
        
        # Check for password reuse
        if PasswordHistory.check_password_reuse(current_user.id, form.new_password.data):
            flash(_t('This password was recently used. Please choose a different one.'), 'danger')
            return render_template('auth/force_password_change.html', form=form)
        
        # Update password and record in history
        old_hash = current_user.password_hash
        current_user.set_password(form.new_password.data)
        PasswordHistory.add_to_history(current_user.id, old_hash)
        db.session.commit()
        
        # Log the change
        AuditHelper.log_password_change(current_user.id)
        
        flash(_t('Password updated successfully'), 'success')
        return redirect(url_for('main.index'))


    return render_template('auth/force_password_change.html', form=form)


@bp.route('/verify-2fa', methods=['GET', 'POST'], endpoint='verify_totp')
@limiter.limit("10 per 15 minutes")
def verify_totp():
    """Verify TOTP code during login"""
    user_id = session.get('totp_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    if not user or not user.totp_enabled:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        use_backup = request.form.get('use_backup') == 'on'
        
        if use_backup:
            # Try backup code
            from app.security import TOTPManager
            verified, remaining_codes = TOTPManager.verify_backup_code(user.totp_backup_codes, code)
            if verified:
                user.totp_backup_codes = remaining_codes
                db.session.commit()
                AuditHelper.log_login_attempt(user, True)
                session['totp_verified'] = True
                login_user(user)
                flash(_t('Login successful'), 'success')
                return redirect(url_for('main.index'))
            else:
                flash(_t('Invalid backup code'), 'danger')
        else:
            # Try TOTP code
            from app.security import TOTPManager
            if TOTPManager.verify_token(user.totp_secret, code):
                AuditHelper.log_login_attempt(user, True)
                session['totp_verified'] = True
                login_user(user)
                flash(_t('Login successful'), 'success')
                return redirect(url_for('main.index'))
            else:
                flash(_t('Invalid 2FA code'), 'danger')
    
    return render_template('auth/verify_2fa.html')


@bp.route('/logout', endpoint='logout')
def logout():
    logout_user()
    flash(_t('You have been logged out successfully'), 'info')
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'], endpoint='register')
def register():
    # registration disabled; only administrators may add accounts via admin panel
    abort(404)
