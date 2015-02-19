from flask.ext.script import Manager

from application import app, engine

manager = Manager(app)

@manager.command
def runEngine():
    engine()

if __name__ == "__main__":
    manager.run()
