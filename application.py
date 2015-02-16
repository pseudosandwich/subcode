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
import re
import pickle

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

    email = request.form['email']
    language = request.form['language']
    print("added user with email", email, "language", language)

    languages = languagesByEmail(email)
    if languages == []:
        #New User
        insertLanguagesByEmail(email, [language, 0])
    else:
        #Old User
        #Test that language is not already in any of the entires
        if all(language not in entry for entry in languages):
            languages.append([language,0])
        updateLanguagesByEmail(email, languages)
        flash('Thanks for signing up!')

    return render_template('index.html', error=error)

@app.route('/db')
def show_entries():
    cur = g.db.execute('select email, languages from users order by id desc')
    ##Being lazy here, but we should eventually implement a good function for taking our querried results and de-pickling them - making individual language by email calls would be network heavy
    entries = [dict(email=row[0], languages=pickle.loads(row[1])) for row in cur.fetchall()]
    print(entries)
    return render_template('db.html', entries=entries)


#send mail
def engine():
    with app.app_context():
        g.db = connect_db()
        print("Sending mail at", datetime.now())
        print(send_mail(g.db))
        g.db.close()

#retrieve languages by email
def languagesByEmail(email):
    cursor = g.db.execute('select languages from users where email=?', (email,))
    return languagesByLanguageCursor(cursor)

#retrieve languages by ID
def languagesByID(id):
    cursor = g.db.execute('select languages from users where id=?', (id,))
    return languagesByLanguageCursor(cursor)

#used to make retrieve languages by email and ID DRY
def languagesByLanguageCursor(cursor):
    languages = []
    entry = cursor.fetchone()
    if entry:
        languageString = entry[0]
        languages = pickle.loads(languageString)
        return languages
    else:
        return []

#insert languages by email
def insertLanguagesByEmail(email, languages):
    g.db.execute('insert or replace into users (email, languages) values (?, ?)', (email, pickle.dumps(languages)))
    g.db.commit()

def updateLanguagesByEmail(email, languages):
    g.db.execute('update users set languages = ? where email = ?', (pickle.dumps(languages), email))
    g.db.commit()

#update languages by ID
def updateLanguagesByID(id, languages):
    g.db.execute('update users set languages = ? where id = ?', (pickle.dumps(languages), id))
    g.db.commit()

#increment timestep by id, language
def incrementTimestep(id, language):
    languages = languagesByID(id)
    for i in range(len(languages)):
        if languages[i][0] == language:
            languages[i][1] += 1;
    updateLanguagesByID(id, languages)


def send_mail(db):
    cur = db.execute('select id, email, languages from users order by id desc')
    entries = [dict(id=row[0], email=row[1], languages=pickle.loads(row[2])) for row in cur.fetchall()]
    for entry in entries:
        for language in entry.get('languages'):
            print("Email:", entry.get('email'), "timestep", language[1], "Languages", language[0], "id", entry.get('id'));
            send_one_message(entry.get('email'), language[1], language[0])
            #update timestep
            incrementTimestep(entry.get('id'), language[0])
    return "Mailed!"

def send_one_message(receiver, day, language):
    code = getSomeCode(day, language)
    if code :
        response = requests.post(
            "https://api.mailgun.net/v2/sandboxc8fa348a2c6240008434768cb8f374cc.mailgun.org/messages",
            auth=("api", config.MAILGUN_KEY),
            data={"from": "Jackson de Campos <jackson@jacksondc.com>",
                  "to": receiver,
                  "subject": "New " + language + " code from Subcode",
                  "html": "We have some new " + language + " code for you:\n\n<code>" + code + "</code>"
                  })
        print('mailed things with response', response)
    else :
        print("No code! Uh-oh!")

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

    print("url", url, "escape", escape)

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
        print("Error in github request", r.content)

def getSomeCode(day, language):
    finalText = ""
    safety = 0

    while(len(finalText) == 0 and safety < 5) :
        safety += 1 #just to make sure we don't go forever
        try:
          API_URL = "https://api.github.com/"

          print('before')
          allResults = makeGithubRequest(API_URL + 'search/repositories?q=' + language + '\&language:' + language + '\&sort\=stars\&order\=desc', True)
          print('after')
          repos = allResults.get('items')
          repo = repos[randint(0, len(repos)-1)]

          owner = repo.get('owner').get('login')
          name = repo.get('name')
          branch = repo.get('default_branch')

          extension = getFileFromLanguage(language)
          searchResults = makeGithubRequest(API_URL + 'search/code?q=' + language
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

          print("ft", finalText)
          print("lines", lines)
          print("path", path)
          print("extension", extension)
          print("owner", owner)
          print("name", name)
        except Exception as e:
          print(e)

    return finalText

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(engine, 'interval', days=1)
    scheduler.start()
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    #send_one_message('jacksondecampos@gmail.com', 10, 'Swift');

    app.run(debug=True, use_reloader=False)

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()  # Not strictly necessary if daemonic mode is enabled but should be done if possible
