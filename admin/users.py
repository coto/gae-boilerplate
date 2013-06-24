# -*- coding: utf-8 -*-
import webapp2
from boilerplate import models
from boilerplate import forms
from boilerplate.handlers import BaseHandler
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from google.appengine.api import users
from collections import OrderedDict, Counter
from wtforms import fields


class AdminLogoutHandler(BaseHandler):
    def get(self):
        self.redirect(users.create_logout_url(dest_url=self.uri_for('home')))


class AdminGeoChartHandler(BaseHandler):
    def get(self):
        users = models.User.query().fetch(projection=['country'])
        users_by_country = Counter()
        for user in users:
            if user.country:
                users_by_country[user.country] += 1
        params = {
            "data": users_by_country.items()
        }
        return self.render_template('admin/geochart.html', **params)


class EditProfileForm(forms.EditProfileForm):
    activated = fields.BooleanField('Activated')


class AdminUserListHandler(BaseHandler):
    def get(self):
        p = self.request.get('p')
        q = self.request.get('q')
        c = self.request.get('c')
        forward = True if p not in ['prev'] else False
        cursor = Cursor(urlsafe=c)

        if q:
            qry = models.User.query(ndb.OR(models.User.last_name == q,
                                           models.User.email == q,
                                           models.User.username == q))
        else:
            qry = models.User.query()

        PAGE_SIZE = 50
        if forward:
            users, next_cursor, more = qry.order(models.User.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            if next_cursor and more:
                self.view.next_cursor = next_cursor
            if c:
                self.view.prev_cursor = cursor.reversed()
        else:
            users, next_cursor, more = qry.order(-models.User.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            users = list(reversed(users))
            if next_cursor and more:
                self.view.prev_cursor = next_cursor
            self.view.next_cursor = cursor.reversed()

        def pager_url(p, cursor):
            params = OrderedDict()
            if q:
                params['q'] = q
            if p in ['prev']:
                params['p'] = p
            if cursor:
                params['c'] = cursor.urlsafe()
            return self.uri_for('user-list', **params)

        self.view.pager_url = pager_url
        self.view.q = q

        params = {
            "list_columns": [('username', 'Username'),
                             ('name', 'Name'),
                             ('last_name', 'Last Name'),
                             ('email', 'Email'),
                             ('country', 'Country'),
                             ('tz', 'TimeZone')],
            "users": users,
            "count": qry.count()
        }
        return self.render_template('admin/list.html', **params)


class AdminUserEditHandler(BaseHandler):
    def get_or_404(self, user_id):
        try:
            user = models.User.get_by_id(long(user_id))
            if user:
                return user
        except ValueError:
            pass
        self.abort(404)

    def edit(self, user_id):
        if self.request.POST:
            user = self.get_or_404(user_id)
            if self.form.validate():
                self.form.populate_obj(user)
                user.put()
                self.add_message("Changes saved!", 'success')
                return self.redirect_to("user-edit", user_id=user_id)
            else:
                self.add_message("Could not save changes!", 'error')
        else:
            user = self.get_or_404(user_id)
            self.form.process(obj=user)

        params = {
            'user': user
        }
        return self.render_template('admin/edit.html', **params)

    @webapp2.cached_property
    def form(self):
        f = EditProfileForm(self)
        f.country.choices = self.countries_tuple
        f.tz.choices = self.tz
        return f
