from boilerplate.models import User
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel
"""
This is an example of a model you could put in your admin
"""
class Example(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    user_name =ndb.StringProperty()
    day = ndb.StringProperty()
    end_date = ndb.DateTimeProperty()
    start_date = ndb.DateTimeProperty()
    certification_name = ndb.StringProperty()
    basic_type = ndb.StringProperty(choices=['Sailing','Windsurfing'])
    sub_type = ndb.StringProperty(choices=['Level 1','Level 2','Level 3'])

    def _pre_put_hook(self):
        if self.user:
            self.user_name = self.user.get().name

