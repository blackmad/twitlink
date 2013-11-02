twitlink
========
powers http://twitlink.blackmad.com/

working twitter/rauth/flask app that saves login credentials in a session
(the rauth docs are broken, they user twitter api v1, the answers on stackoverflow for saving sessions don't quite 
work either)

you'll want to create an application.cfg that looks like
SECRET_KEY = '[randomness goes here]'
TWITTER_CONSUMER_KEY = 'XXXXXXXXX'
TWITTER_CONSUMER_SECRET = 'XXXXXXXXX'

get key/secret from https://dev.twitter.com/apps

Make sure you app has a callback url (doesn't matter what, the app specifies a redirect, but twitter won't 
use it unless something is filled into this field) and that 'allow ... sign in with twitter' is checked as well.

happy hacking. issues/comments/complaints/praise to david@blackmad.com
