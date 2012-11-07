from boilerplate.models import User
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

class Lesson(ndb.Model):


    day = ndb.StringProperty()
    end_date = ndb.DateTimeProperty()
    start_date = ndb.DateTimeProperty()
    certification_name = ndb.StringProperty()
    basic_type = ndb.StringProperty(choices=['Sailing','Windsurfing'])
    sub_type = ndb.StringProperty(choices=['Level 1','Level 2','Level 3'])

class User(User):
    pass


