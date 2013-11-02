try:
  from flaskext.sqlalchemy import SQLAlchemy
except:
  from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Link(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    expanded_url = db.Column(db.String(500), unique=False)

    def __init__(self, id, expanded_url):
        self.id = id
        self.expanded_url = expanded_url

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    fb_id = db.Column(db.String(120))
    psession = db.Column(db.String(2020))
    access_token = db.Column(db.String(120))
    access_token_secret = db.Column(db.String(120))

    def __init__(self, username, fb_id, s, at, ats):
        self.username = username
        self.fb_id = fb_id
        self.psession = s
        self.access_token = at
        self.access_token_secret = ats

    def __repr__(self):
        return '<User %r>' % self.username

    @staticmethod
    def get_or_create(username, fb_id, psession, access_token, access_token_secret):
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = User(username, fb_id, psession, access_token, access_token_secret)
            db.session.add(user)
        else:
            user.psession = psession
            user.access_token = access_token
            user.access_token_secret = access_token_secret
        db.session.commit()
        return user

