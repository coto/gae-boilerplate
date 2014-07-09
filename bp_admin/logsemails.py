# -*- coding: utf-8 -*-
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from collections import OrderedDict
from bp_includes.lib.basehandler import BaseHandler
from bp_includes.models import LogEmail


class AdminLogsEmailsHandler(BaseHandler):
    def get(self):
        p = self.request.get('p')
        q = self.request.get('q')
        c = self.request.get('c')
        forward = True if p not in ['prev'] else False
        cursor = Cursor(urlsafe=c)

        if q:
            qry = LogEmail.query(ndb.OR(LogEmail.to == q.lower(),
                                           LogEmail.sender == q.lower(),
                                           LogEmail.subject == q.lower()))
        else:
            qry = LogEmail.query()

        PAGE_SIZE = 50
        if forward:
            emails, next_cursor, more = qry.order(LogEmail.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            if next_cursor and more:
                self.view.next_cursor = next_cursor
            if c:
                self.view.prev_cursor = cursor.reversed()
        else:
            emails, next_cursor, more = qry.order(-LogEmail.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            emails = list(reversed(emails))
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
            return self.uri_for('admin-logs-emails', **params)

        self.view.pager_url = pager_url
        self.view.q = q

        params = {
            "list_columns": [('when', 'When'),
                             ('to', 'To'),
                             ('subject', 'Subject'),
                             ('sender', 'Sender'),
            #                 ('body', 'Body')
            ],
            "emails": emails,
            "count": qry.count()
        }
        return self.render_template('admin_logs_emails.html', **params)


class AdminLogsEmailViewHandler(BaseHandler):
    def get(self, email_id):
        try:
            emaildata = LogEmail.get_by_id(long(email_id))
            if emaildata:
                params = {
                    'emailinfo': emaildata
                }
                return self.render_template('admin_logs_email_view.html', **params)
        except ValueError:
            pass
        self.abort(404)
