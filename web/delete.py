# -*- coding: utf-8 -*-

"""
	A real simple app for using webapp2 with auth and session.

	It just covers the basics. Creating a user, login, logout and a decorator for protecting certain handlers.

    Routes are setup in routes.py and added in main.py

"""

__author__ = 'Rodrigo Augosto (@coto)'
__website__ = 'www.protoboard.cl'

import logging, webapp2
from models import User


class DeleteKindHandler(webapp2.RequestHandler):
    def get(self):
        """
        Create/Delete Kinds from Datastore slowly
        Just use one of the following eaxmples
        """

        ###### CREATE #####
        #        temp = Temp(
        #            name = "juan",
        #            value = "pedro"
        #        )
        #        temp.put()

        ###### Delete User Entity #####
        result = User.query()
        for t in result:
            t._key.delete()
            logging.info("%s deleted" % t._key.id())

        ###### Delete Unique Entity #####
        from webapp2_extras.appengine.auth.models import Unique
        result = Unique.query()
        for t in result:
            t._key.delete()
            logging.info("%s deleted" % t._key.id())

        logging.info(">>>>>>>End of Delete Kind Handler<<<<<<<")