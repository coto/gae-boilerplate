import logging
import webapp2
from webapp2_extras import jinja2
from webapp2_extras import auth
from webapp2_extras import sessions
from lib import utils
import config
import re
from lib import i18n
from babel import Locale
import models.models as models

def user_required(handler):
    """
         Decorator for checking if there's a user associated
         with the current session.
         Will also fail if there's no session present.
    """

    def check_login(self, *args, **kwargs):
        """
            If handler has no login_url specified invoke a 403 error
        """
        try:
            auth = self.auth.get_user_by_session()
            if not auth:
                try:
                    self.redirect(self.auth_config['login_url'], abort=True)
                except (AttributeError, KeyError), e:
                    self.abort(403)
            else:
                return handler(self, *args, **kwargs)
        except AttributeError, e:
            # avoid AttributeError when the session was delete from the server
            logging.error(e)
            self.auth.unset_session()
            self.redirect_to('home')

    return check_login

def jinja2_factory(app):
    j = jinja2.Jinja2(app)
    j.environment.filters.update({
        # Set filters.
        # ...
    })
    j.environment.globals.update({
        # Set global variables.
        'uri_for': webapp2.uri_for,
        'getattr': getattr,
        'str': str
    })
    j.environment.tests.update({
        # Set tests.
        # ...
    })
    return j

def handle_error(request, response, exception):
    c = { 'exception': str(exception) }
    status_int = hasattr(exception, 'status_int') and exception.status_int or 500
    template = config.error_templates[status_int]
    t = jinja2.get_jinja2(factory=jinja2_factory, app=webapp2.get_app()).render_template(template, **c)
    logging.error(str(status_int) + " - " + str(exception))
    response.write(t)
    response.set_status(status_int)


class BaseHandler(webapp2.RequestHandler):
    """
        BaseHandler for all requests

        Holds the auth and session properties so they
        are reachable for all requests
    """

    def __init__(self, request, response):
        """ Override the initialiser in order to set the language.
        """
        self.initialize(request, response)
        self.locale = i18n.set_locale(self)

    def dispatch(self):
        """
            Get a session store for this request.
        """
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def auth(self):
        return auth.get_auth()

    @webapp2.cached_property
    def session_store(self):
        return sessions.get_store(request=self.request)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()

    @webapp2.cached_property
    def messages(self):
        return self.session.get_flashes(key='_messages')

    def add_message(self, message, level=None):
        self.session.add_flash(message, level, key='_messages')

    @webapp2.cached_property
    def auth_config(self):
        """
              Dict to hold urls for login/logout
        """
        return {
            'login_url': self.uri_for('login'),
            'logout_url': self.uri_for('logout')
        }

    @webapp2.cached_property
    def user(self):
        return self.auth.get_user_by_session()

    @webapp2.cached_property
    def user_id(self):
        return str(self.user['user_id']) if self.user else None

    @webapp2.cached_property
    def user_key(self):
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            return user_info.key
        return  None

    @webapp2.cached_property
    def username(self):
        if self.user:
            try:
                user_info = models.User.get_by_id(long(self.user_id))
                return str(user_info.username)
            except AttributeError, e:
                # avoid AttributeError when the session was delete from the server
                logging.error(e)
                self.auth.unset_session()
                self.redirect_to('home')
        return  None

    @webapp2.cached_property
    def email(self):
        if self.user:
            try:
                user_info = models.User.get_by_id(long(self.user_id))
                return user_info.email
            except AttributeError, e:
                # avoid AttributeError when the session was delete from the server
                logging.error(e)
                self.auth.unset_session()
                self.redirect_to('home')
        return  None

    @webapp2.cached_property
    def path_for_language(self):
        """
        Get the current path + query_string without language parameter (hl=something)
        Useful to put it on a template to concatenate with '&hl=NEW_LOCALE'
        Example: .../?hl=en_US
        """
        path_lang = re.sub(r'(^hl=(\w{5})\&*)|(\&hl=(\w{5})\&*?)', '', str(self.request.query_string))

        return self.request.path + "?" if path_lang == "" else str(self.request.path) + "?" + path_lang

    def locales(self):
        """
        returns a dict of locale codes to locale display names in both the current locale and the localized locale
        example: if the current locale is es_ES then locales['en_US'] = 'Ingles (Estados Unidos) - English (United States)'
        """
        locales = {}
        for l in config.locales:
            current_locale = Locale.parse(self.locale)
            language = current_locale.languages[l.split('_')[0]]
            territory = current_locale.territories[l.split('_')[1]]
            localized_locale_name = Locale.parse(l).display_name
            locales[l] = language + " (" + territory + ") - " + localized_locale_name
        return locales

    @webapp2.cached_property
    def is_mobile(self):
        return utils.set_device_cookie_and_return_bool(self)

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(factory=jinja2_factory, app=self.app)

    def render_template(self, filename, **kwargs):
        kwargs.update({
            'google_analytics_code' : config.google_analytics_code,
            'app_name': config.app_name,
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'url': self.request.url,
            'path': self.request.path,
            'query_string': self.request.query_string,
            'path_for_language': self.path_for_language,
            'is_mobile': self.is_mobile,
            'locale': Locale.parse(self.locale), # babel locale object
            'locales': self.locales()
            })
        kwargs.update(self.auth_config)
        if self.messages:
            kwargs['messages'] = self.messages

        self.response.headers.add_header('X-UA-Compatible', 'IE=Edge,chrome=1')
        self.response.write(self.jinja2.render_template(filename, **kwargs))