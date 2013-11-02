'''
    facebook
    --------

    A simple Flask demo app that shows how to login with Facebook via rauth.

    Please note: you must do `from facebook import db; db.create_all()` from
    the interpreter before running this example!
    
    Due to Facebook's stringent domain validation, requests using this app 
    must originate from 127.0.0.1:5000.
'''

from flask import Flask, flash, request, redirect, render_template, url_for, session, escape
from flask.ext.sqlalchemy import SQLAlchemy

from rauth.service import OAuth2Service, OAuth1Service
from rauth.utils import parse_utf8_qsl
from werkzeug import BaseResponse
import pickle
import twitter
import pytz
from datetime import  datetime
from dateutil.tz import tzoffset
import urlparse

# Flask config
SQLALCHEMY_DATABASE_URI = 'sqlite:///twitter.db'
DEBUG = True

# Flask setup
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_pyfile("application.cfg", silent=True)
db = SQLAlchemy(app)

# rauth OAuth 2.0 service wrapper
twitterAuth = OAuth1Service(
    consumer_key=app.config['TWITTER_CONSUMER_KEY'],
    consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
    name='twitter',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authorize',
    request_token_url='https://api.twitter.com/oauth/request_token',
    base_url='https://api.twitter.com/1.1/')

class Link(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    expanded_url = db.Column(db.String(500), unique=False)

    def __init__(self, id, expanded_url):
        self.id = id
        self.expanded_url = expanded_url

# models
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


# views
@app.route('/')
def index():
    if 'username' in session:
      sess = try_login()
      if sess:
        max_id = request.args.get('max_id', None)
        params={'format':'json', 'count': 200}
        if max_id:
          params['max_id'] = max_id
        timeline = sess.get('statuses/home_timeline.json', params=params).json()
        # get a 'tzinfo' instance with the UTC offset for the user's local time
        theUser = sess.get('users/show.json', params={'screen_name': session['username']}).json()
        statuses = [twitter.Status.NewFromJsonDict(s) for s in timeline]
        return statusview_helper(twitter.User.NewFromJsonDict(theUser), statuses, None)
      else:
        return render_template('login.html')
    return render_template('login.html')


@app.route('/twitter/login')
def login():
    oauth_callback = 'http://twitlink.blackmad.com/twitter/authorized'

    params = {'oauth_callback': oauth_callback}

    r = twitterAuth.get_raw_request_token(params=params)

    data = parse_utf8_qsl(r.content)
    print data

    session['twitter_oauth'] = (data['oauth_token'],
                                data['oauth_token_secret'])

    return redirect(twitterAuth.get_authorize_url(data['oauth_token'], **params))

def try_login():
    try:
      user = User.query.filter_by(username=session['username']).first()
      sess = pickle.loads(user.psession)
    except Exception, e:
        flash('There was a problem logging into Twitter: ' + str(e))
        return None
   
    return sess

@app.route('/twitter/authorized')
def authorized():
    request_token, request_token_secret = session.pop('twitter_oauth')

    # check to make sure the user authorized the request
    if not 'oauth_token' in request.args:
        flash('You did not authorize the request')
        return redirect(url_for('index'))

    try:
        creds = {'request_token': request_token,
                'request_token_secret': request_token_secret}
        params = {'oauth_verifier': request.args['oauth_verifier']}
        sess = twitterAuth.get_auth_session(params=params, **creds)
    except Exception, e:
        flash('There was a problem logging into Twitter: ' + str(e))
        return redirect(url_for('index'))
   
    verify = sess.get('account/verify_credentials.json', params={'format':'json'}).json()

    User.get_or_create(verify['screen_name'], verify['id'],
      pickle.dumps(sess),
      sess.access_token, sess.access_token_secret)
    session['username'] = verify['screen_name']

    flash('Logged in as ' + verify['name'])
    return redirect(url_for('index'))
 
def musicFilter(s):
  musicWords = [
    'music',
    'remix',
    'sound',
    'hear',
    'listen',
    'jazz',
    'tune',
    'funk',
    'ambient',
    'mix',
    'album',
    'jam',
    'song',
    'electronica'
  ]
  for m in musicWords:
    if m in s.text:
      return True
  return False

def defaultFilter(s):
  mediaDomains = [
    '4sq.com', 'vine.co', 'flick', 'instagr.am', 'instagram', '.jpg', 'rd.io'
  ]
  for u in s.urls:
    for m in mediaDomains:
      if m in u.expanded_url:
        return False
  return True

@app.route('/<user>/music')
def userviewMusic(user):
  return userview_helper(user, musicFilter)

@app.route('/<user>')
def userview(user):
  return userview_helper(user, None)

def userview_helper(user, statusFilter):
  api = twitter.Api(consumer_key=app.config['TWITTER_CONSUMER_KEY'],
    consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
    access_token_key=app.config['TWITTER_ACCESS_TOKEN_KEY'],
    access_token_secret=app.config['TWITTER_ACCESS_TOKEN_SECRET'])
  max_id = request.args.get('max_id', None)

  # get a 'tzinfo' instance with the UTC offset for the user's local time
  theUser = api.GetUser(screen_name=user)
  print 'user %s' % theUser

  statuses = api.GetUserTimeline(screen_name=user, count=200, max_id=max_id)
  return statusview_helper(theUser, statuses, statusFilter)

def statusview_helper(theUser, statuses, statusFilter):
  if statusFilter:
    statuses = [s for s in statuses if statusFilter(s)]
  statuses = [s for s in statuses if defaultFilter(s)]
  content = ''

  import re
  two_letter_re = re.compile('.*\.../.*')
  all_short_urls = []
  unshort_dict = {}
  for s in statuses:
    for u in s.urls:
      if (two_letter_re.match(u.expanded_url) or
          'tinyurl' in u.expanded_url or
          len(urlparse.urlparse(u.expanded_url).netloc) == 6):
        existing_link = Link.query.filter_by(id=u.expanded_url).first()
        if existing_link:
          if existing_link.expanded_url != '0':
            unshort_dict[u.expanded_url] = existing_link.expanded_url
        else:
          all_short_urls.append(u.expanded_url)
  print all_short_urls
  import urllib
  import json
  for k,v in json.loads(urllib.urlopen('http://urlex.org/json/' + '***'.join(all_short_urls)).read()).items():
    unshort_dict[k] = v
    db.session.add(Link(k, v))
  db.session.commit()
  
  localtime_tz = tzoffset(theUser.time_zone, theUser.utc_offset)

  for s in statuses:
    if s.urls:
      text = s.text
      for u in s.urls:
        expanded = unshort_dict.get(u.expanded_url)

        if expanded:
          u.expanded_url = expanded
        text = text.replace(u.url, '<a href="%s">%s</a>' % (u.expanded_url, u.expanded_url))
      utc_dt = datetime.utcfromtimestamp(s.created_at_in_seconds).replace(tzinfo=pytz.utc)
      localtime_dt = utc_dt.astimezone(localtime_tz)

      content += render_template('tweet.html',
        text = text,
        tweetLink = 'http://twitter.com/%s/status/%s' % (theUser.screen_name, s.id) ,
        postedAt = localtime_dt.strftime("%a, %b %d %Y %I:%M%p"),
        postedBy = s.user.screen_name,
        urls = [u.expanded_url for u in s.urls],
        user = theUser
      )
  
  content += '<br><h2><a href="?max_id=%s">Next Page</a><h2>' % statuses[-1].id
  return render_template('index.html', content=content, user=theUser)


if __name__ == '__main__':
    db.create_all()
    app.run(port=15000)
