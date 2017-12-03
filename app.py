import flask_login
import datetime
from flask import Flask, render_template, json, request, redirect, url_for, jsonify
from flask_security import Security, SQLAlchemySessionUserDatastore, login_required, login_user, logout_user, current_user
from flask_security.utils import encrypt_password
from wtforms import Form, PasswordField, TextField
from wtforms.validators import DataRequired
from celery import Celery
from database.database import db_session, init_db
from database.models import User, Role, Source, SourceLog, Text
from crawler.preview import get_preview
from crawler.Crawl import crawl_scrape

def make_celery(app):
    celery = Celery(app.name, backend=app.config['CELERY_RESULT_BACKEND'],
                    broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
            celery.Task = ContextTask
    return celery

app = Flask(__name__)
app.config['DEBUG'] = False
app.config['SECRET_KEY'] = 'super-secret'
app.config['SECURITY_PASSWORD_SALT'] = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
app.config['SECURITY_PASSWORD_HASH'] = 'pbkdf2_sha512'
app.config['SECURITY_LOGIN_USER_TEMPLATE'] = 'login.html'
app.config['CELERY_BROKER_URL'] = 'amqp://swissal:password@localhost:5672/swissalvhost'
app.config['CELERY_RESULT_BACKEND'] = 'database'
app.config['CELERY_RESULT_DBURI'] = 'sqlite:///tmp_celery.db'
app.config['CELERY_IMPORTS'] = ['__main__']
celery = make_celery(app)

# Setup Flask-Security
user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
security = Security(app, user_datastore)

# Create a user to test with
@app.before_first_request
def before_first_request():
    init_db()
    user_datastore.find_or_create_role(name='admin', description='Administrator')
    user_datastore.find_or_create_role(name='user', description='User')
    user_datastore.find_or_create_role(name='operator', description='Operator')
    encrypted_password = encrypt_password('password')
    if not user_datastore.get_user('admin@admin.com'):
        user_datastore.create_user(email='admin@admin.com', username='admin', password='password')
    if not user_datastore.get_user('operator@operator.com'):
        user_datastore.create_user(email='operator@operator.com', username='operator', password='password')
    db_session.commit()
    user_datastore.add_role_to_user('admin@admin.com', 'admin')
    user_datastore.add_role_to_user('operator@operator.com', 'operator')
    db_session.commit()

@app.route('/')
@login_required
def main():
    overview = {'num_html_files': 0, 'num_pdf_files': 0, 'num_html_tokens': 0, 'num_pdf_tokens': 0, 'srclogs':[]}
    all_sources = db_session.query(Source).all()
    for s in all_sources:
        overview['num_html_files'] += s.num_files_html
        overview['num_pdf_files'] += s.num_files_pdf
    all_texts = db_session.query(Text).filter(Text.ftype=='html').all()
    for at in all_texts:
        overview['num_html_tokens'] += at.num_token
    all_texts = db_session.query(Text).filter(Text.ftype=='pdf').all()
    for at in all_texts:
        overview['num_pdf_tokens'] += at.num_token
    overview['num_de'] = len(db_session.query(Text).filter(Text.lang=='de').all())
    overview['num_fr'] = len(db_session.query(Text).filter(Text.lang=='fr').all())
    overview['num_it'] = len(db_session.query(Text).filter(Text.lang=='it').all())
    overview['num_en'] = len(db_session.query(Text).filter(Text.lang=='en').all())

    slogs = db_session.query(SourceLog).all()
    for s in slogs:
        overview['srclogs'].append({"username":s.username, "srcname": s.srcname, "timestamp":s.timestamp})
    return render_template('index.html', overview=overview)

@app.route('/load_overview')
@login_required
def load_overview():
    pass

@app.route('/sources')
@login_required
def sources():
    ans = db_session.query(Source).all()
    sources=[]
    for a in ans:
        elem = {}
        elem['name'] = a.name
        elem['crawling'] = a.crawling
        elem['dname'] = a.domain
        elem['num_tok_pdf'] = str(a.num_token_pdf)
        elem['num_tok_html'] = str(a.num_token_html)
        elem['num_files_pdf'] = str(a.num_files_pdf)
        elem['num_files_html'] = str(a.num_files_html)
        sources.append(elem)
    return render_template('sources.html', sources=sources)

@app.route('/query')
@login_required
def query():
    return render_template('query.html')

@app.route('/new_source')
@login_required
def newSource():
    return render_template('new_source.html')

@app.route('/load_preview')
@login_required
def load_preview():
    dname = request.args.get('dname', default='', type=str)
    previews = get_preview(dname)
    for i in range(0, len(previews)):
        previews[i] = previews[i].decode('latin-1')
    res = {"page": previews}
    return jsonify(res)

@app.route('/save_source')
@login_required
def save_source():
    name = request.args.get('name', default='', type=str)
    dname = request.args.get('dname', default='', type=str)
    xp_title = request.args.get('xp_title', default='', type=str)
    xp_lead = request.args.get('xp_lead', default='', type=str)
    xp_content = request.args.get('xp_content', default='', type=str)
    xp_date = request.args.get('xp_date', default='', type=str)
    xp_author = request.args.get('xp_author', default='', type=str)
    xp_keywords = request.args.get('xp_keywords', default='', type=str)
    f_title = request.args.get('f_title', default='', type=str)
    f_lead = request.args.get('f_lead', default='', type=str)
    f_content = request.args.get('f_content', default='', type=str)
    f_date = request.args.get('f_date', default='', type=str)
    f_author = request.args.get('f_author', default='', type=str)
    f_keywords = request.args.get('f_keywords', default='', type=str)
    print current_user.username
    try:
        src = Source(name=name, domain=dname, xp_title=xp_title, xp_lead=xp_lead, xp_content=xp_content, xp_date=xp_date, xp_author=xp_author, xp_keywords=xp_keywords, f_title=f_title, f_lead=f_lead, f_content=f_content, f_date=f_date, f_author=f_author, f_keywords=f_keywords)
        db_session.add(src)
        srclog = SourceLog(srcname=name, username=current_user.username, timestamp=datetime.datetime.now())
        db_session.add(srclog)
        db_session.commit()
    except:
        return "error"
    return "saved"

@app.route('/start_source')
#@login_required
def start_source():
    dname = request.args.get('dname', default='', type=str)
    t = task_source.delay(dname)
    return "done"


@celery.task()
def task_source(dname):
    from celery import current_task
    import os
    import subprocess
    with app.app_context():
        crawl_scrape(dname)


@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
