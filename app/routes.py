from flask import Blueprint, render_template, session, redirect, request, url_for, jsonify, current_app
from flask_login import login_required

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/lang/<lang>')
def set_language(lang):
    if lang not in ('en', 'es'):
        lang = 'en'
    session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))


@bp.route('/debug/db', methods=['GET'])
@login_required
def debug_db():
    """Debug endpoint to show which database is being used (admin only)"""
    from flask_login import current_user
    if not current_user.is_admin():
        return jsonify({'error': 'Admin access required'}), 403
    
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')
    # Mask password for security
    if db_uri and '://' in db_uri:
        parts = db_uri.split('://')
        if '@' in parts[1]:
            user_pass, host = parts[1].split('@')
            db_uri_masked = f"{parts[0]}://***:***@{host}"
        else:
            db_uri_masked = db_uri
    else:
        db_uri_masked = db_uri
    
    db_type = 'PostgreSQL' if 'postgresql' in (db_uri or '').lower() else 'SQLite'
    
    return jsonify({
        'database_type': db_type,
        'database_uri_masked': db_uri_masked,
        'environment': current_app.config.get('ENV', 'unknown'),
        'debug_mode': current_app.debug
    })
