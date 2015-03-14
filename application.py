# all the imports
import requests
from datetime import datetime
import time
from flask import Flask, request, render_template, flash, g, url_for, redirect
from contextlib import closing
import os
from apscheduler.schedulers.background import BackgroundScheduler
import json
import base64
from random import randint
import re
import json
from flask.ext.sqlalchemy import SQLAlchemy
import psycopg2
import os
from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.lexers import guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name

#Environment variables:
try:
    from config import *
except ImportError:
    print("No config file - using environment vairables")
    GITHUB_ID = os.environ['GITHUB_ID']
    GITHUB_SECRET = os.environ['GITHUB_SECRET']
    MAILGUN_API_KEY = os.environ['MAILGUN_API_KEY']
    MAILGUN_BASE_URL = os.environ['MAILGUN_BASE_URL']
    SQLALCHEMY_DATABASE_URI = os.environ['SQLALCHEMY_DATABASE_URI']
    DEBUG = (os.environ['DEBUG'] == "True")
    SECRET_KEY = os.environ['SECRET_KEY']
    USERNAME = os.environ['USERNAME']
    PASSWORD = os.environ['PASSWORD']
    PYGMENTS_STYLE = os.environ['PYGMENTS_STYLE']
    BASE_URL = os.environ['BASE_URL']
    if DEBUG:
        ENGINE_HOUR = os.environ['ENGINE_HOUR']
        ENGINE_MINUTE = os.environ['ENGINE_MINUTE']



app = Flask(__name__)
app.config.from_object(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db = SQLAlchemy(app)
#IMPORTANT THAT THIS REMAIN AFTER THE DECLERATION OF DB BECAUSE MODELS IMPORTS DB

from models import *
#database initialization


def init_db():
    db.create_all()


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

    if languages == None:
        #New User
        insertLanguagesByEmail(email, [[language, 0]])
    else:
        #Old User
        #Test that language is not already in any of the entires
        if all(language not in entry for entry in languages):
            languages.append([language,0])
        updateLanguagesByEmail(email, languages)

    flash('Thanks for signing up!')

    return render_template('index.html', error=error)

@app.route('/unsubscribe/<email>/<language>')
def unsubscribe(email, language):
    error = None

    print("unsubscribe user with email", email, "language", language)

    languages = languagesByEmail(email)

    for i in range(len(languages)):
        if languages[i][0] == language:
            del languages[i]

    updateLanguagesByEmail(email, languages);

    flash("You have been unsubscribed from " + str(language))
    return redirect(url_for('hello'))


if DEBUG:
    @app.route('/db')
    def show_entries():
        cur = User.query.all()
        ##Being lazy here, but we should eventually implement a good function for taking our querried results and de-pickling them - making individual language by email calls would be network heavy
        entries = [dict(email=row.email, languages=json.loads(row.languages)) for row in cur]
        return render_template('db.html', entries=entries)


#send mail
def engine():
    print("Sending mail at", datetime.now())
    print(send_mail(db))

#retrieve languages by email
def languagesByEmail(email):
    entry = User.query.filter_by(email=email).first()
    if entry:
        return json.loads(entry.languages)
    else:
        return None



#retrieve languages by ID
def languagesByID(id):
    entry = User.query.filter_by(id=id).first()
    if entry:
        return json.loads(entry.languages)
    else:
        return None

#insert languages by email
def insertLanguagesByEmail(email, languages):
    user = User(email, json.dumps(languages))
    db.session.add(user)
    db.session.commit()

#update languages by email
def updateLanguagesByEmail(email, languages):
    entry = User.query.filter_by(email=email).first()
    entry.languages = json.dumps(languages)
    db.session.commit()

#update languages by ID
def updateLanguagesByID(id, languages):
    entry = User.query.filter_by(id=id).first()
    entry.languages = json.dumps(languages)
    db.session.commit()



#increment timestep by id, language
def incrementTimestep(id, language):
    languages = languagesByID(id)
    for i in range(len(languages)):
        if languages[i][0] == language:
            languages[i][1] += 1;
    updateLanguagesByID(id, languages)


def send_mail(db):
    cur = User.query.all()
    entries = [dict(id=row.id, email=row.email, languages=json.loads(row.languages)) for row in cur]
    for entry in entries:
        for language in entry.get('languages'):
            print("Email:", entry.get('email'), "timestep", language[1], "Languages", language[0], "id", entry.get('id'));
            send_one_message(entry.get('email'), language[1], language[0])
            #update timestep
            incrementTimestep(entry.get('id'), language[0])
    return "Mailed!"

#Returns stylesheet for given pygments style
def styleSheet(style):
    return '''<style type=\"text/css\">
        a
        {
          color: black;
          text-decoration: none;
        }
        div.unsubscribe
        {
          display: inline-block;
          background:transparent;
          border:1px solid #ddd;
          border-radius:4px;
          margin:0 auto;
          margin:0.5rem;
          padding:0.5rem;
        }''' \
        + HtmlFormatter(style=style).get_style_defs() + "\n.container {border:solid gray;border-width:.1em .1em .1em .8em;padding:.2em .6em;}" + "</style>"

def send_one_message(receiver, day, language):
    code = getSomeCode(day, language)
    if code :
        with app.test_request_context():
            formattedCode = highlight(code, get_lexer_for_filename('.'+getFileFromLanguage(language)), HtmlFormatter(linenos=True))
            print(formattedCode)
            response = requests.post(
                MAILGUN_BASE_URL+"/messages",
                auth=("api", MAILGUN_API_KEY),
                data={"from": "Subcode <smulumudi@gmail.com>",
                      "to": receiver,
                      "subject": "New " + language + " code from Subcode",
                      "html": '''
                      <head>
                        %(styleSheet)s
                      </head>
                      <body>
                      We have some new %(language)s code for you:

                      <div class=\"container hll\">
                      %(formattedCode)s
                      </div>
                      <div class="buttons">
                      <a href=%(unsubscribeURL)s><div class="unsubscribe">Unsubscribe from %(language)s</div></a>
                      </div>
                      </body>
                      ''' % {'styleSheet': styleSheet(PYGMENTS_STYLE), 'language': language, 'formattedCode': formattedCode, 'email': receiver, 'unsubscribeURL': BASE_URL + url_for('unsubscribe', email=receiver, language=language)}
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
        fullUrl = url + '\&client_id\=' + GITHUB_ID + '\&client_secret\=' + GITHUB_SECRET
    else :
        fullUrl = url + '&client_id=' + GITHUB_ID + '&client_secret=' + GITHUB_SECRET

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
        time.sleep(12)
        safety += 1 #just to make sure we don't go forever
        try:
          API_URL = "https://api.github.com/"

          allResults = makeGithubRequest(API_URL + 'search/repositories?q=' + language + '\&language:' + language + '\&sort\=stars\&order\=desc', True)
          repos = allResults.get('items')
          repo = repos[randint(0, len(repos)-1)]

          owner = repo.get('owner').get('login')
          name = repo.get('name')
          branch = repo.get('default_branch')

          extension = getFileFromLanguage(language)
          searchResults = makeGithubRequest(API_URL + 'search/code?q=' + "%20"
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
    if DEBUG:
        scheduler = BackgroundScheduler()
        scheduler.add_job(engine, 'cron', hour=ENGINE_HOUR, minute=ENGINE_MINUTE)
        scheduler.start()

    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    #send_one_message('jacksondecampos@gmail.com', 10, 'Swift');
    app.run(debug=DEBUG, use_reloader=False)

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()  # Not strictly necessary if daemonic mode is enabled but should be done if possible
