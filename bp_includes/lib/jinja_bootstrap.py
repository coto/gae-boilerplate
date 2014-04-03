import webapp2
from webapp2_extras import jinja2
from webapp2_extras import sessions
from bp_includes.lib import utils

def generate_csrf_token():
    session = sessions.get_store().get_session()
    if '_csrf_token' not in session:
        session['_csrf_token'] = utils.random_string()
    return session['_csrf_token']

def jinja2_factory(app):
    j = jinja2.Jinja2(app)
    j.environment.filters.update({
        # Set filters.
        # ...
    })
    j.environment.globals.update({
        # Set global variables.
        'csrf_token': generate_csrf_token,
        'uri_for': webapp2.uri_for,
        'getattr': getattr,
    })
    j.environment.tests.update({
        # Set test.
        # ...
    })
    return j
