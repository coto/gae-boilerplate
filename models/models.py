from webapp2_extras.appengine.auth.models import User
from google.appengine.ext import ndb

class User(User):
    """
    Universal user model. Can be used with App Engine's default users API,
    own auth or third party authentication methods (OpenId, OAuth etc).
    based on https://gist.github.com/kylefinley
    """

    #: Creation date.
    created = ndb.DateTimeProperty(auto_now_add=True)
    #: Modification date.
    updated = ndb.DateTimeProperty(auto_now=True)
    #: User defined unique name, also used as key_name.
    username = ndb.StringProperty(required=True)
    #: User Name
    name = ndb.StringProperty()
    #: User Last Name
    last_name = ndb.StringProperty()
    #: User email
    email = ndb.StringProperty(required=True)
    #: Password, only set for own authentication.
    password = ndb.StringProperty(required=True)
    #: User Country
    country = ndb.StringProperty()
    
    @classmethod
    def get_by_email(cls, email):
        """Returns a user object based on an email.

        :param email:
            String representing the user email. Examples:

        :returns:
            A user object.
        """
        return cls.query(cls.email == email).get()

class VisitLog(ndb.Model):
    user = ndb.KeyProperty(kind=User)
    uastring = ndb.StringProperty()
    ip = ndb.StringProperty()
    timestamp = ndb.StringProperty()