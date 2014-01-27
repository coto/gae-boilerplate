# -*- coding: utf-8 -*-
from boilerplate.handlers import BaseHandler
from google.appengine.api import users


class AdminLogoutHandler(BaseHandler):
    def get(self):
        self.redirect(users.create_logout_url(dest_url=self.uri_for('home')))
