from application import db
from sqlalchemy.dialects.postgresql import JSON

class User(db.Model):
    __tablename__ = 'users'

    uuid = db.Column(db.String(), primary_key=True)
    email = db.Column(db.String(), unique=True, nullable=False)
    languages = db.Column(JSON)
    verified = db.Column(db.Boolean(), nullable=False, default=False)

    def __init__(self, uuid, email, languages, confirmed=False):
        self.uuid =uuid
        self.email = email
        self.languages = languages
        self.confirmed = confirmed

    def __repr__(self):
        return '<id {}>'.format(self.uuid)
