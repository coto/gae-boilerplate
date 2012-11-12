# -*- coding: utf-8 -*-
from boilerplate.handlers import BaseHandler
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from google.appengine.ext.ndb.query import FilterNode
from collections import OrderedDict
from boilerplate.external.wtforms import fields
import logging
import admin.forms
logger = logging.getLogger(__name__)
from admin.forms import *
import routes



class List(BaseHandler):
    model_class=None
    form_class=None
    def post(self,*args,**kwargs):
        action= self.request.get("action")
        id = self.request.get("id")
        user = ndb.Key(urlsafe=id)
        user.delete()
        self.get(*args,**kwargs)

    def get(self,*args,**kwargs):
        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        p = self.request.get('p')
        q = self.request.get('q')
        c = self.request.get('c')
        forward = True if p not in ['prev'] else False
        cursor = Cursor(urlsafe=c)
        from google.appengine.ext.ndb.query import Node
        if q:
            nodes=[]
            for search in self.form_class.search_list:
                nodes.append(FilterNode(search,'=',q))
            qry = self.model_class.query(ndb.OR(*nodes))

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
            return self.uri_for('%s-list'%self.model_class.__name__, **params)

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

    def get_or_404(self, id,*args,**kwargs):
        try:
            logger.warn("the user id: %s "%id)
            user = ndb.Key(urlsafe=id).get()
            if user:
                return user
        except ValueError:
            pass
        self.abort(404)



    def add (self, *args, **kwargs):
        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        self.form=self.form_class(self)

        #user=self.model_class()
        #user.put()
        if self.request.POST:

            user =self.model_class()
            user.put()
            if self.form.validate():
                self.form.populate_obj(user)
                user.put()
                self.add_message("Changes saved!", 'success')
                return self.redirect_to("%s-edit"%self.model_class.__name__.lower(), id=user.key.urlsafe())
            else:
                self.add_message("Could not save changes!", 'error')

        params = {
            'user' : None,
            'pretty_name': self.model_class.__name__
        }
        return self.render_template('admin/edit.html', **params)

    def edit(self, id,*args,**kwargs):
        user = None
        self.model_class=kwargs['_class']
        self.form_class=kwargs['_form_class']
        self.form=self.form_class(self)

        if self.request.POST:
            user = self.get_or_404(id)
            if self.form.validate():
                self.form.populate_obj(user)
                user.put()
                self.add_message("Changes saved!", 'success')
                return self.redirect_to("%s-edit"%self.model_class.__name__.lower(), id=id)
            else:
                self.add_message("Could not save changes!", 'error')
        else:
            user = self.get_or_404(id)
            self.form.process(obj=user)

        params = {
            'user' : user,
            'pretty_name': self.model_class.__name__
        }
        return self.render_template('admin/edit.html', **params)

class Home(BaseHandler):
    def get(self,*args,**kwargs):
        class_list=[]
        for model in routes.models:
            model_params={}
            model_params['name']=model['class'].__name__
            model_params['link']=self.uri_for('%s-list'%model['class'].__name__.lower())
            model_params['add_uri']=self.uri_for('%s-add'%model['class'].__name__.lower())
            class_list.append(model_params)
        params = {
            'class_list': class_list
        }
        return self.render_template('admin/home.html', **params)