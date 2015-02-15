# all the imports
import sqlite3
import requests
from datetime import datetime
import time
from flask import Flask, request, render_template, flash, g
from contextlib import closing
import os
from apscheduler.scheduler import Scheduler

def tick():
    print('Tick! The time is: %s' % datetime.now())

# configuration
DATABASE = '/tmp/flaskr.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

app = Flask(__name__)
app.config.from_object(__name__)

#database initialization
def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

#before an http request, open a database connection
@app.before_request
def before_request():
    g.db = connect_db() # the g object does magical things to store data across one request

#after an http request, close the database connection
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route("/")
def hello():
    return render_template('index.html')


@app.route('/', methods=['POST'])
def get_email():
    error = None

    text = request.form['email']
    language = request.form['language']
    print("added user with email", text, "language", language)

    g.db.execute( 'insert into users (email, language) values (?, ?)',
                  [ request.form['email'], request.form['language'] ] )
    g.db.commit()
    flash('Thanks for signing up!')

    return render_template('index.html', error=error)

@app.route('/db')
def show_entries():
    cur = g.db.execute('select email, language from users order by id desc')
    entries = [dict(email=row[0], language=row[1]) for row in cur.fetchall()]
    return render_template('db.html', entries=entries)


#send mail
"""sched = Scheduler()
sched.daemonic = False
sched.start()

def engine():
    db = connect_db()

    print("Sending mail at", datetime.datetime.now())
    send_mail(db)
    time.sleep(20)

    db.close()

# Schedules job_function to be run once each minute
sched.add_cron_job(engine,  minute='0-59')"""

def send_mail(db):
    cur = db.execute('select email, language from users order by id desc')
    entries = [dict(email=row[0], language=row[1]) for row in cur.fetchall()]
    for entry in entries :
        send_one_message(entry.get('email'))
    return "Mailed!"

def send_one_message(receiver):
    response = requests.post(
        "https://api.mailgun.net/v2/sandboxc8fa348a2c6240008434768cb8f374cc.mailgun.org/messages",
        auth=("api", "key-446186653236f98dfccf322d4eb6aa16"),
        data={"from": "Mailgun Sandbox <postmaster@sandboxc8fa348a2c6240008434768cb8f374cc.mailgun.org>",
              "to": receiver,
              "subject": "New code from Subcode",
              "text": "Some code!"})
    print('mailed things with response', response)

if __name__ == "__main__":
    app.run(debug=True)
    scheduler = BackgroundScheduler()
    scheduler.add_job(tick, 'interval', seconds=5)
    scheduler.start()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()  # Not strictly necessary if daemonic mode is enabled but should be done if possible