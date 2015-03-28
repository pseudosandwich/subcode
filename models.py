from application import db
from sqlalchemy.dialects.postgresql import JSON

class User(db.Model):
    __tablename__ = 'users'

    uuid = db.Column(db.String(), primary_key=True)
    email = db.Column(db.String(), unique=True)
    languages = db.Column(JSON)

    def __init__(self, uuid, email, languages):
        self.uuid =uuid
        self.email = email
        self.languages = languages

    def __repr__(self):
        return '<id {}>'.format(self.uuid)
