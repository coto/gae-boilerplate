# *-* coding: UTF-8 *-*

# standard library imports
import logging
import re
# related third party imports
import webapp2
from google.appengine.api.users import NotAllowedError
from webapp2_extras import jinja2
from webapp2_extras import auth
from webapp2_extras import sessions
from google.appengine.api import taskqueue
# local application/library specific imports
from boilerplate import models
from boilerplate.lib import utils, i18n
from babel import Locale

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
        'csrf_token' : generate_csrf_token,
        'uri_for': webapp2.uri_for,
        'getattr': getattr,
        'str': str
    })
    j.environment.tests.update({
        # Set test.
        # ...
    })
    return j

def handle_error(request, response, exception):
    c = {
        'exception': str(exception),
        'url': request.url,
        }

    if request.app.config.get('send_mail_developer') is not False:
        # send email
        subject         = request.app.config.get('app_name') + " error."
        email_body_path = "emails/error.txt"
        message         = 'This error was looking for you: ' + c['exception'] + ' from ' + c['url']

        if c['exception'] is not 'Error saving Email Log in datastore':
            template_val = {
                "app_name"  : request.app.config.get('app_name'),
                "message"   : message,
                }

            email_body = jinja2.get_jinja2(factory=jinja2_factory, app=webapp2.get_app()).render_template(email_body_path, **template_val)
            email_url = webapp2.uri_for('taskqueue-send-email')

            for dev in request.app.config.get('developers'):
                taskqueue.add(url = email_url, params={
                    'to':       dev[1],
                    'subject' : subject,
                    'body' :    email_body,
                    'sender' :  request.app.config.get('contact_sender'),
                    })

    status_int = hasattr(exception, 'status_int') and exception.status_int or 500
    template = request.app.config.get('error_templates')[status_int]
    t = jinja2.get_jinja2(factory=jinja2_factory, app=webapp2.get_app()).render_template(template, **c)
    logging.error(str(status_int) + " - " + str(exception))
    response.write(t)
    response.set_status(status_int)

class ViewClass:
    """
        ViewClass to insert variables into the template.

        ViewClass is used in BaseHandler to promote variables automatically that can be used
        in jinja2 templates.
        Use case in a BaseHandler Class:
            self.view.var1 = "hello"
            self.view.array = [1, 2, 3]
            self.view.dict = dict(a="abc", b="bcd")
        Can be accessed in the template by just using the variables liek {{var1}} or {{dict.b}}
    """
    pass


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
        self.view = ViewClass()

    def dispatch(self):
        """
            Get a session store for this request.
        """
        self.session_store = sessions.get_store(request=self.request)

        try:
            # csrf protection
            if self.request.method == "POST" and not self.request.path.startswith('/taskqueue'):
                token = self.session.get('_csrf_token')
                if not token or token != self.request.get('_csrf_token'):
                    self.abort(403)

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
    def language(self):
        return str(Locale.parse(self.locale).language)

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
    def provider_uris(self):
        from google.appengine.api import users
        try:
            provider_info = models.SocialUser.PROVIDERS_INFO
            login_urls = {}
            for provider in provider_info:
                provider_uri = provider_info[provider]['uri']
                if provider_uri:
                    login_urls[provider] = users.create_login_url(federated_identity=provider_uri, dest_url=self.uri_for('social-login-complete', provider_name=provider))
                else:
                    login_urls[provider] = self.uri_for("social-login", provider_name=provider)
            return login_urls
        except NotAllowedError:
            self.response.write('<p class="alert alert-error"><a class="close" data-dismiss="alert">x</a> '
                                'You must enable Federated Login Before for this application.<br> '
                                '<a href="http://appengine.google.com" target="_blank">Google App Engine Control Panel</a> -> '
                                'Administration -> Application Settings -> Authentication Options</p>')

    @webapp2.cached_property
    def provider_info(self):
        return models.SocialUser.PROVIDERS_INFO

    @webapp2.cached_property
    def path_for_language(self):
        """
        Get the current path + query_string without language parameter (hl=something)
        Useful to put it on a template to concatenate with '&hl=NEW_LOCALE'
        Example: .../?hl=en_US
        """
        path_lang = re.sub(r'(^hl=(\w{5})\&*)|(\&hl=(\w{5})\&*?)', '', str(self.request.query_string))

        return self.request.path + "?" if path_lang == "" else str(self.request.path) + "?" + path_lang

    @property
    def locales(self):
        """
        returns a dict of locale codes to locale display names in both the current locale and the localized locale
        example: if the current locale is es_ES then locales['en_US'] = 'Ingles (Estados Unidos) - English (United States)'
        """
        if not self.app.config.get('locales'):
            return None
        locales = {}
        for l in self.app.config.get('locales'):
            current_locale = Locale.parse(self.locale)
            language = current_locale.languages[l.split('_')[0]]
            territory = current_locale.territories[l.split('_')[1]]
            localized_locale_name = Locale.parse(l).display_name.capitalize()
            locales[l] = language.capitalize() + " (" + territory.capitalize() + ") - " + localized_locale_name
        return locales

    @webapp2.cached_property
    def is_mobile(self):
        return utils.set_device_cookie_and_return_bool(self)

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(factory=jinja2_factory, app=self.app)

    @webapp2.cached_property
    def get_base_layout(self):
        """
        Get the current base layout template for jinja2 templating. Uses the variable base_layout set in config
        or if there is a base_layout defined, use the base_layout.
        """
        return self.base_layout if hasattr(self, 'base_layout') else self.app.config.get('base_layout')

    def set_base_layout(self, layout):
        """
        Set the base_layout variable, thereby overwriting the default layout template name in config.py.
        """
        self.base_layout = layout

    def render_template(self, filename, **kwargs):
        locales = self.app.config.get('locales') or []
        locale_iso = None
        language = ''
        territory = ''
        language_id = self.app.config.get('app_lang')

        if self.locale and len(locales) > 1:
            locale_iso = Locale.parse(self.locale)
            language_id = locale_iso.language
            territory_id = locale_iso.territory
            language = locale_iso.languages[language_id]
            territory = locale_iso.territories[territory_id]

        # make all self.view variables available in jinja2 templates
        if hasattr(self, 'view'):
            kwargs.update(self.view.__dict__)

        # set or overwrite special vars for jinja templates
        kwargs.update({
            'google_analytics_domain' : self.app.config.get('google_analytics_domain'),
            'google_analytics_code' : self.app.config.get('google_analytics_code'),
            'app_name': self.app.config.get('app_name'),
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'url': self.request.url,
            'path': self.request.path,
            'query_string': self.request.query_string,
            'path_for_language': self.path_for_language,
            'is_mobile': self.is_mobile,
            'locale_iso': locale_iso, # babel locale object
            'locale_language': language.capitalize() + " (" + territory.capitalize() + ")", # babel locale object
            'locale_language_id': language_id, # babel locale object
            'locales': self.locales,
            'provider_uris': self.provider_uris,
            'provider_info': self.provider_info,
            'enable_federated_login': self.app.config.get('enable_federated_login'),
            'base_layout': self.get_base_layout
            })
        kwargs.update(self.auth_config)
        if hasattr(self, 'form'):
            kwargs['form'] = self.form
        if self.messages:
            kwargs['messages'] = self.messages

        self.response.headers.add_header('X-UA-Compatible', 'IE=Edge,chrome=1')
        self.response.write(self.jinja2.render_template(filename, **kwargs))