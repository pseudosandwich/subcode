from application import db
from sqlalchemy.dialects.postgresql import JSON

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String())
    languages = db.Column(JSON)

    def __init__(self, email, languages):
        self.email = email
        self.languages = languages

    def __repr__(self):
        return '<id {}>'.format(self.id)
