# -*- coding: utf-8 -*-
from boilerplate.handlers import BaseHandler
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from collections import OrderedDict
from wtforms import fields
import logging

logger = logging.getLogger(__name__)
from admin.forms import *



class List(BaseHandler):
    model_class=None
    form_class=None

    def get(self,*args,**kwargs):
        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        p = self.request.get('p')
        q = self.request.get('q')
        c = self.request.get('c')
        forward = True if p not in ['prev'] else False
        cursor = Cursor(urlsafe=c)

        if q:
            qry = self.model_class.query(ndb.OR(self.model_class.last_name == q,
                                           self.model_class.email == q,
                                           self.model_class.username == q))
        else:
            qry = self.model_class.query()

        PAGE_SIZE = 5
        if forward:
            users, next_cursor, more = qry.order(self.model_class.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            if next_cursor and more:
                self.view.next_cursor = next_cursor
            if c:
                self.view.prev_cursor = cursor.reversed()
        else:
            users, next_cursor, more = qry.order(-self.model_class.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
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
            "class_name": self.model_class.__name__,
            "list_columns": self.form_class.list_columns,
            "users" : users,
            "count" : qry.count(),
            'add_uri': self.uri_for('%s-add'%self.model_class.__name__.lower())
        }
        logger.warn(params)
        return self.render_template('admin/list.html', **params)


class Edit(BaseHandler):
    form_class=None
    model_class=None

    def get_or_404(self, user_id,*args,**kwargs):
        try:
            logger.warn("the user id: %s "%user_id)
            user = ndb.Key(urlsafe=user_id).get()
            if user:
                return user
        except ValueError:
            pass
        self.abort(404)

    def delete (self, user_id,  *args, **kwargs):
        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        user = ndb.Key(urlsafe=user_id)
        user.delete()
        return self.redirect_to("%s-list"%self.model_class.__name__.lower())


    def add (self, *args, **kwargs):
        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        user=self.model_class()
        user.put()
        logger.warn("The key:%s "%user.key.urlsafe())
        return self.redirect_to("%s-edit"%self.model_class.__name__.lower(), user_id=user.key.urlsafe())

    def edit(self, user_id,*args,**kwargs):

        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        self.form=self.form_class(self)

        if self.request.POST:
            user = self.get_or_404(user_id)
            if self.form.validate():
                self.form.populate_obj(user)
                user.put()
                self.add_message("Changes saved!", 'success')
                return self.redirect_to("%s-edit"%self.model_class.__name__.lower(), user_id=user_id)
            else:
                self.add_message("Could not save changes!", 'error')
        else:
            user = self.get_or_404(user_id)
            self.form.process(obj=user)

        params = {
            'user' : user,
            'pretty_name': self.model_class.__name__
        }
        return self.render_template('admin/edit.html', **params)


