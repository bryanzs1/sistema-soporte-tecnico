from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter.util import get_remote_address
import os
import hashlib
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app import db, login, translate, limiter, send_email
from app.models import User
from app.forms import LoginForm, ForcePasswordChangeForm, ChangePasswordForm, RequestPasswordResetForm, ResetPasswordForm
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


def _login_rate_limit_key():
    """Scope login limiting by client IP + submitted username to reduce shared-network collisions."""
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    ip = forwarded_for.split(',')[0].strip() if forwarded_for else get_remote_address()
    username = (request.form.get('username') or '').strip().lower() or '__empty__'
    return f"{ip}:{username}"


def _password_reset_serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])


def _generate_password_reset_token(user):
    # Bind token to current password hash so old links die immediately after a password change.
    password_hash_digest = hashlib.sha256((user.password_hash or '').encode('utf-8')).hexdigest()
    payload = {'uid': user.id, 'ph': password_hash_digest}
    return _password_reset_serializer().dumps(payload, salt='password-reset')


def _resolve_user_from_reset_token(token, max_age_seconds=1800):
    try:
        data = _password_reset_serializer().loads(token, salt='password-reset', max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None

    user = User.query.get(data.get('uid'))
    if not user or not user.is_active:
        return None

    expected_digest = hashlib.sha256((user.password_hash or '').encode('utf-8')).hexdigest()
    if data.get('ph') != expected_digest:
        return None

    return user


def _login_fail_redirect():
    """Redirect after a failed login attempt.

    When the request came from the login modal (source=modal in POST data),
    redirect back to the referring page with ?login_failed=1 so the modal
    can re-open automatically.  Falls back to the normal login page."""
    if request.form.get('source') == 'modal':
        referrer = request.referrer or ''
        host_url = request.host_url.rstrip('/')
        # Same-origin check to prevent open redirect
        if referrer and (referrer == host_url or referrer.startswith(host_url + '/')):
            base = referrer.split('?')[0].split('#')[0]
            return redirect(base + '?login_failed=1')
        return redirect(url_for('main.index') + '?login_failed=1')
    return redirect(url_for('main.index') + '?login_failed=1')


@bp.route('/login', methods=['GET', 'POST'], endpoint='login')
@limiter.limit("5 per 15 minutes", key_func=_login_rate_limit_key, methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'GET':
        query_flag = 'login_failed=1' if request.args.get('login_failed') else 'open_login=1'
        return redirect(url_for('main.index') + f'?{query_flag}')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        # Check if account is locked due to failed attempts
        if user and user.is_account_locked():
            AuditHelper.log_login_attempt(user, False)
            flash(_t('Account is locked due to multiple failed login attempts. Try again later.'), 'danger')
            return _login_fail_redirect()
        
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
            return _login_fail_redirect()
        
        # Check if account is active
        if not user.is_active:
            AuditHelper.log_login_attempt(user, False)
            # Si la empresa está desactivada, mostrar razón
            company = user.company
            if company and not company.is_active:
                reason = company.deactivation_reason or _t('Su empresa está inactiva. Contacte a soporte.')
                flash(_t(f'Acceso denegado: {reason}'), 'danger')
            else:
                flash(_t('Esta cuenta ha sido desactivada. Contacte a un administrador.'), 'danger')
            return _login_fail_redirect()
        
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
    return redirect(url_for('main.index') + '?open_login=1')


@bp.route('/forgot-password', methods=['GET', 'POST'], endpoint='forgot_password')
@limiter.limit('5 per hour', methods=['POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        email = (form.email.data or '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user and user.is_active:
            token = _generate_password_reset_token(user)
            reset_url = url_for('auth.reset_password_with_token', token=token, _external=True)
            subject = _t('Password reset link')
            body = _t('Open this link to reset your password: {url}').format(url=reset_url)
            try:
                send_email(subject, [user.email], body)
            except Exception as e:
                current_app.logger.error('Error sending password reset email to %s: %s', user.email, e)

        # Prevent account enumeration by always returning the same response.
        flash(_t('If the email exists in our system, you will receive password reset instructions shortly.'), 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'], endpoint='reset_password_with_token')
@limiter.limit('10 per hour', methods=['POST'])
def reset_password_with_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user = _resolve_user_from_reset_token(token)
    if not user:
        flash(_t('Invalid or expired password reset link. Request a new one.'), 'danger')
        return redirect(url_for('auth.forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        from app.security import PasswordValidator
        from app.models import PasswordHistory

        is_valid, message = PasswordValidator.validate(form.new_password.data)
        if not is_valid:
            flash(_t('Password does not meet security requirements: ') + message, 'warning')
            return render_template('auth/reset_password.html', form=form)

        if PasswordHistory.check_password_reuse(user.id, form.new_password.data):
            flash(_t('This password was recently used. Please choose a different one.'), 'danger')
            return render_template('auth/reset_password.html', form=form)

        if user.check_password(form.new_password.data):
            flash(_t('New password must be different from current password'), 'warning')
            return render_template('auth/reset_password.html', form=form)

        old_hash = user.password_hash
        user.set_password(form.new_password.data)
        PasswordHistory.add_to_history(user.id, old_hash, commit=False)
        db.session.commit()

        try:
            AuditHelper.log_password_change(user.id)
        except Exception as audit_error:
            current_app.logger.warning('Audit log failed after self-service password reset: %s', audit_error)

        flash(_t('Your password has been reset successfully. Please sign in.'), 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', form=form)


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
        
        # Update password and record in history using one transaction.
        old_hash = current_user.password_hash
        current_user.set_password(form.new_password.data)
        PasswordHistory.add_to_history(current_user.id, old_hash, commit=False)
        db.session.commit()
        
        # Log the change
        AuditHelper.log_password_change(current_user.id)
        
        flash(_t('Password updated successfully'), 'success')
        return redirect(url_for('main.index'))


    return render_template('auth/force_password_change.html', form=form)


@bp.route('/change-password', methods=['GET', 'POST'], endpoint='change_password')
@login_required
def change_password():
    """Allow users to change their password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash(_t('Current password is incorrect'), 'danger')
            return render_template('auth/change_password.html', form=form)
        
        # Validate password strength
        from app.security import PasswordValidator
        from app.models import PasswordHistory
        
        is_valid, message = PasswordValidator.validate(form.new_password.data)
        if not is_valid:
            flash(_t('Password does not meet security requirements: ') + message, 'warning')
            return render_template('auth/change_password.html', form=form)
        
        # Check for password reuse
        if PasswordHistory.check_password_reuse(current_user.id, form.new_password.data):
            flash(_t('This password was recently used. Please choose a different one.'), 'danger')
            return render_template('auth/change_password.html', form=form)
        
        # Check if new password is same as current
        if current_user.check_password(form.new_password.data):
            flash(_t('New password must be different from current password'), 'warning')
            return render_template('auth/change_password.html', form=form)
        
        # Update password and record in history using one transaction.
        old_hash = current_user.password_hash
        current_user.set_password(form.new_password.data)
        PasswordHistory.add_to_history(current_user.id, old_hash, commit=False)
        db.session.commit()
        
        # Log the change
        AuditHelper.log_password_change(current_user.id)
        
        flash(_t('Password changed successfully'), 'success')
        return redirect(url_for('main.index'))
    
    return render_template('auth/change_password.html', form=form)


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
