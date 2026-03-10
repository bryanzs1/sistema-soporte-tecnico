from flask import Blueprint, render_template, session, redirect, request, url_for, jsonify
from flask_login import login_required

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({'status': 'healthy', 'service': 'soporte-tecnico'}), 200


@bp.route('/presence-ping', methods=['GET'])
@login_required
def presence_ping():
    """Lightweight endpoint to keep authenticated user presence up to date."""
    return ('', 204)


@bp.route('/lang/<lang>')
def set_language(lang):
    if lang not in ('en', 'es'):
        lang = 'en'
    session['lang'] = lang
    return redirect(request.referrer or url_for('main.index'))


@bp.route('/quienes-somos')
def about_us():
    return render_template('about.html')


@bp.route('/terminos-y-condiciones')
def terms_and_conditions():
    return render_template('terms.html')


