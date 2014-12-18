# -*- coding: utf-8 -*-
from google.appengine.datastore.datastore_query import Cursor
from google.appengine.ext import ndb
from collections import OrderedDict
from bp_includes.lib.basehandler import BaseHandler
from bp_includes.models import LogVisit
from bp_includes.models import User


class AdminLogsVisitsHandler(BaseHandler):
    def get(self):
        p = self.request.get('p')
        q = self.request.get('q')
        c = self.request.get('c')
        forward = True if p not in ['prev'] else False
        cursor = Cursor(urlsafe=c)

        if q:
            user_key = ndb.Key(User,long(q.lower()))
            qry = LogVisit.query(ndb.OR(   LogVisit.user == user_key,
                                            LogVisit.timestamp == q.lower(),
                                            LogVisit.uastring == q.lower(),
                                            LogVisit.ip == q.lower()))
        else:
            qry = LogVisit.query()

        PAGE_SIZE = 50
        if forward:
            visits, next_cursor, more = qry.order(LogVisit.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            if next_cursor and more:
                self.view.next_cursor = next_cursor
            if c:
                self.view.prev_cursor = cursor.reversed()
        else:
            visits, next_cursor, more = qry.order(-LogVisit.key).fetch_page(PAGE_SIZE, start_cursor=cursor)
            visits = list(reversed(visits))
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
            return self.uri_for('admin-logs-visits', **params)

        self.view.pager_url = pager_url
        self.view.q = q

        params = {
            "list_columns": [('timestamp', 'Timestamp'),
                             ('ip', 'IP'),
                             ('uastring', 'uastring')
            ],
            "visits": visits,
            "count": qry.count()
        }
        return self.render_template('admin_logs_visits.html', **params)
