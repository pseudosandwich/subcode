# all the imports
import sqlite3
import requests
from datetime import datetime
import time
from flask import Flask, request, render_template, flash, g
from contextlib import closing
import os
from apscheduler.schedulers.background import BackgroundScheduler
import json
import base64
from random import randint
import config

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

    g.db.execute( 'insert into users (email, timestep, language) values (?, ?, ?)',
                  [ request.form['email'], 0, request.form['language'] ] )
    g.db.commit()
    flash('Thanks for signing up!')

    return render_template('index.html', error=error)

@app.route('/db')
def show_entries():
    cur = g.db.execute('select email, language from users order by id desc')
    entries = [dict(email=row[0], language=row[1]) for row in cur.fetchall()]
    return render_template('db.html', entries=entries)


#send mail
def engine():
    db = connect_db()
    print("Sending mail at", datetime.now())
    print(send_mail(db))
    db.close()

def send_mail(db):
    cur = db.execute('select id, email, language, timestep from users order by id desc')
    entries = [dict(id=row[0], email=row[1], language=row[2], timestep=row[3]) for row in cur.fetchall()]
    for entry in entries :
        print("Email:", entry.get('email'), "timestep", entry.get('timestep'), "Language", entry.get('language'), "id", entry.get('id'));
        send_one_message(entry.get('email'), entry.get('timestep'), entry.get('language'))
        #update timestep
        db.execute('update users set timestep=timestep+1 where id=?', entry.get('id'))
    return "Mailed!"

def send_one_message(receiver, day, language):
    """response = requests.post(
        "https://api.mailgun.net/v2/sandboxc8fa348a2c6240008434768cb8f374cc.mailgun.org/messages",
        auth=("api", config.MAILGUN_KEY),
        data={"from": "Mailgun Sandbox <postmaster@sandboxc8fa348a2c6240008434768cb8f374cc.mailgun.org>",
              "to": receiver,
              "subject": "New code from Subcode",
              "text": "Here's some new Swift code: " + getSomeCode(day, language)})"""
    print('mailed things with response') #, response)

def getFileFromLanguage(language):
    langs = {
        'ActionScript': 'as',
        'C': 'c',
        'C#': 'cs',
        'C++': 'cpp',
        'Clojure': 'clj',
        'CoffeeScript': 'coffee',
        'Common Lisp': 'lisp',
        'CSS': 'css',
        'Emacs Lisp': 'lisp',
        'Erlang': 'erl',
        'Haskell': 'hs',
        'HTML': 'html',
        'Java': 'java',
        'JavaScript': 'js',
        'Lua': 'lua',
        'Objective-C': 'm',
        'Perl': 'pl', # || pl'
        'PHP': 'php',
        'Python': 'py',
        'Ruby': 'rb',
        'Scala': 'scala',
        'Scheme': 'ss', # || scm || sch'
        'Swift': 'swift',
        'Shell': 'sh',
        'SQL': 'sql'
    };
    return langs[language];

def makeGithubRequest(url, escape):

    if not '?' in url :
        url += '?'

    fullUrl = ""
    if escape:
        fullUrl = url + '\&client_id\=' + config.GITHUB_ID + '\&client_secret\=' + config.GITHUB_SECRET
    else :
        fullUrl = url + '&client_id=' + config.GITHUB_ID + '&client_secret=' + config.GITHUB_SECRET
    r = requests.get(fullUrl)

    if(r.ok):
        allResults = json.loads(r.text or r.content)
        return allResults
    else :
        print("Error in github request", r.content())

def getSomeCode(day, language):
    finalText = ""
    safety = 0

    while(len(finalText) == 0 and safety < 5) :
        safety += 1 #just to make sure we don't go forever
        try:
          API_URL = "https://api.github.com/"

          allResults = makeGithubRequest(API_URL + 'search/repositories?q=swift\&language:' + language
                                                 + '\&sort\=stars\&order\=desc', True)

          repos = allResults.get('items')
          repo = repos[randint(0, len(repos)-1)]

          owner = repo.get('owner').get('login')
          name = repo.get('name')
          branch = repo.get('default_branch')

          extension = getFileFromLanguage(language)
          searchResults = makeGithubRequest(API_URL + 'search/code?q=swift+language:' + language
                                            + '+extension:' + extension + '+repo:' + owner + '/' + name, False)

          results = searchResults.get('items')
          result = results[randint(0, len(results)-1)]
          path = result.get('path')

          fileResult = makeGithubRequest(API_URL + "repos/" + owner + "/" + name + "/contents/" + path, False)
          file = fileResult.get('content')
          plaintext = base64.b64decode(file).decode()

          lines = plaintext.split('\n')
          totalLines = (day + 1) * 2

          startLine = randint(0, len(lines) - totalLines)

          finalText = ""
          for i in range(totalLines) :
              finalText += lines[startLine + i] + "\n"

          """print("ft", finalText)
          print("lines", lines)
          print("path", path)
          print("extension", extension)
          print("owner", owner)
          print("name", name)"""
        except:
          pass

    return finalText

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(engine, 'interval', minutes=1)
    scheduler.start()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    app.run(debug=True, use_reloader=False)

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()  # Not strictly necessary if daemonic mode is enabled but should be done if possible
