from google.appengine.ext import ndb
from bp_includes.lib.basehandler import BaseHandler
from bp_includes.models import User
import datetime


class AdminCleanupTokensHandler(BaseHandler):
    def get(self):
        # parameter in timedelta() assumes that tokens expire ~1 month1 after creation:
        pastdate = (datetime.datetime.utcnow() - datetime.timedelta(1*365/12))
        expiredTokens = User.token_model.query(User.token_model.created <= pastdate)
        tokensToDelete = expiredTokens.count()
        # delete the tokens in bulks of 100:
        while expiredTokens.count() > 0:
            keys = expiredTokens.fetch(100, keys_only=True)
            ndb.delete_multi(keys)

        self.response.write('looking for tokens <= %s<br>%s tokens deleted <br> <a href=%s>home</a>' % (pastdate,tokensToDelete, self.uri_for('home')))