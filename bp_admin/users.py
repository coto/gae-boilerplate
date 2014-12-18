# -*- coding: utf-8 -*-
import webapp2
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from collections import OrderedDict, Counter
from wtforms import fields
from bp_includes import forms
from bp_includes.lib.basehandler import BaseHandler


class AdminUserGeoChartHandler(BaseHandler):
    def get(self):
        users = self.user_model.query().fetch(projection=['country'])
        users_by_country = Counter()
        for user in users:
            if user.country:
                users_by_country[user.country] += 1
        params = {
            "data": users_by_country.items()
        }
        return self.render_template('admin_users_geochart.html', **params)


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
            qry = self.user_model.query(ndb.OR(self.user_model.last_name == q.lower(),
                                           self.user_model.email == q.lower(),
                                           self.user_model.username == q.lower()))
        else:
            qry = self.user_model.query()

        PAGE_SIZE = 50
        if forward:
            users, next_cursor, more = qry.order(self.user_model.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            if next_cursor and more:
                self.view.next_cursor = next_cursor
            if c:
                self.view.prev_cursor = cursor.reversed()
        else:
            users, next_cursor, more = qry.order(-self.user_model.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
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
            return self.uri_for('admin-users-list', **params)

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
        return self.render_template('admin_users_list.html', **params)


class AdminUserEditHandler(BaseHandler):
    def get_or_404(self, user_id):
        try:
            user = self.user_model.get_by_id(long(user_id))
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
                return self.redirect_to("admin-user-edit", user_id=user_id)
            else:
                self.add_message("Could not save changes!", 'danger')
        else:
            user = self.get_or_404(user_id)
            self.form.process(obj=user)

        params = {
            'user': user
        }
        return self.render_template('admin_user_edit.html', **params)

    @webapp2.cached_property
    def form(self):
        f = EditProfileForm(self)
        f.country.choices = self.countries_tuple
        f.tz.choices = self.tz
        return f
