from flask import Blueprint, render_template, session, redirect, request, url_for
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


