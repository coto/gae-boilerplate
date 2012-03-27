# -*- coding: utf-8 -*-

"""
	A real simple app for using webapp2 with auth and session.

	It just covers the basics. Creating a user, login, logout
	and a decorator for protecting certain handlers.

    Routes are setup in routes.py and added in main.py

"""

from webapp2_extras.appengine.auth.models import User
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError
from lib import utils
from lib.basehandler import BaseHandler
from lib.basehandler import user_required

# Just for Google Login
from google.appengine.api import users
from google.appengine.api import taskqueue
from webapp2_extras.appengine.users import login_required


class HomeRequestHandler(BaseHandler):

    def get(self):
        """
              Returns a simple HTML form for home
        """
        params = {}
        return self.render_template('home.html', **params)


class PasswordResetHandler(BaseHandler):
    #TODO: Finish this handler
    def get(self):
        if self.user:
            self.redirect_to('secure', id=self.user_id)
        params = {
            'action': self.request.url,
        }
        return self.render_template('password_reset.html', **params)

    def post(self):
        email = self.request.POST.get('email')
        auth_id = "own:%s" % email
        user = User.get_by_auth_id(auth_id)
        if user is not None:
            # Send Message Received Email
            taskqueue.add(url='/emails/password/reset', params={
                'recipient_id': user.key.id(),
                })
            _message = 'Password reset instruction have been sent to %s. Please check your inbox.' % email
            self.add_message(_message, 'success')
            return self.redirect_to('login')
        _message = 'Your email address was not found. Please try another or <a href="/register">create an account</a>.'
        self.add_message(_message, 'error')
        return self.redirect_to('password-reset')


class PasswordResetCompleteHandler(BaseHandler):
    #TODO: Finish this handler
    def get(self, token):
        # Verify token
        token = User.token_model.query(User.token_model.token == token).get()
        if token is None:
            self.add_message('The token could not be found, please resubmit your email.', 'error')
            self.redirect_to('password-reset')
        params = {
            'action': self.request.url,
            }
        return self.render_template('password_reset_complete.html', **params)

    def post(self, token):
        if self.form.validate():
            token = User.token_model.query(User.token_model.token == token).get()
            # test current password
            user = User.get_by_id(int(token.user))
            if token and user:
                user.password = security.generate_password_hash(self.form.password.data, length=12)
                user.put()
                # Delete token
                token.key.delete()
                # Login User
                self.auth.get_user_by_password(user.auth_ids[0], self.form.password.data)
                self.add_message('Password changed successfully', 'success')
                return self.redirect_to('profile-show', id=user.key.id())

        self.add_message('Please correct the form errors.', 'error')
        return self.get(token)


class LoginHandler(BaseHandler):

    def get(self):
        """
              Returns a simple HTML form for login
        """
        if self.user:
            self.redirect_to('secure', id=self.user_id)
        params = {
            "action": self.request.url,
        }
        return self.render_template('login.html', **params)

    def post(self):
        """
              username: Get the username from POST dict
              password: Get the password from POST dict
        """
        username = self.request.POST.get('username')
        password = self.request.POST.get('password')
        remember_me = True if self.request.POST.get('remember_me') == 'on' else False
        # Try to login user with password
        # Raises InvalidAuthIdError if user is not found
        # Raises InvalidPasswordError if provided password
        # doesn't match with specified user
        try:
            self.auth.get_user_by_password(
                username, password, remember=remember_me)
            self.redirect('/')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            # Currently no message is attached to the exceptions
            message = "Login error, Try again"
            self.add_message(message, 'error')
            return self.redirect_to('login')


class CreateUserHandler(BaseHandler):

    def get(self):
        """
              Returns a simple HTML form for create a new user
        """
        if self.user:
            self.redirect_to('secure', id=self.user_id)
        params = {
            "action": self.request.url,
            }
        return self.render_template('create_user.html', **params)

    def post(self):
        """
              username: Get the username from POST dict
              password: Get the password from POST dict
        """
        username = str(self.request.POST.get('username')).lower().strip()
        name = str(self.request.POST.get('name')).strip()
        last_name = str(self.request.POST.get('last_name')).strip()
        email = str(self.request.POST.get('email')).lower().strip()
        password = str(self.request.POST.get('password')).strip()
        c_password = str(self.request.POST.get('c_password')).strip()
        country = str(self.request.POST.get('country')).strip()

        if username == "" or email == "" or password == "":
            message = 'Sorry, some fields are required.'
            self.add_message(message, 'error')
            return self.redirect_to('create-user')

        if password != c_password:
            message = 'Sorry, Passwords are not identical, ' \
                      'you have to repeat again.'
            self.add_message(message, 'error')
            return self.redirect_to('create-user')

        if not utils.is_email_valid(email):
            message = 'Sorry, the email %s is not valid.' % email
            self.add_message(message, 'error')
            return self.redirect_to('create-user')

        if not utils.is_alphanumeric(username):
            message = 'Sorry, the username %s is not valid. ' \
                      'Use only letters and numbers' % username
            self.add_message(message, 'error')
            return self.redirect_to('create-user')

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username','email']
        user = self.auth.store.user_model.create_user(
            username, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            country=country, ip=self.request.remote_addr,
        )

        if not user[0]: #user is a tuple
            message = 'Sorry, User {0:>s} ' \
                      'is already created.'.format(username)# Error message
            self.add_message(message, 'error')
            return self.redirect_to('create-user')
        else:
            # User is created, let's try redirecting to login page
            try:
                message = 'User %s created successfully.' % ( str(username) )
                self.add_message(message, 'info')
                self.redirect(self.auth_config['login_url'])
            except (AttributeError, KeyError), e:
                message = 'Unexpected error creating ' \
                          'user {0:>s}.'.format(username)
                self.add_message(message, 'error')
                self.abort(403)


class LogoutHandler(BaseHandler):
    """
         Destroy user session and redirect to login
    """

    def get(self):
        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            message = "User is logged out." # Info message
            self.add_message(message, 'info')
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            return "User is logged out, but there was an error " \
                   "on the redirection."


class SecureRequestHandler(BaseHandler):
    """
         Only accessible to users that are logged in
    """

    @user_required
    def get(self, **kwargs):
        user_session = self.auth.get_user_by_session()
        user_session_object = self.auth.store.get_session(self.request)

        import models
        user_info = models.User.get_by_id(long( user_session['user_id'] ))
        user_info_object = self.auth.store.user_model.get_by_auth_token(
            user_session['user_id'], user_session['token'])

#        people = models.User.get_by_sponsor_key(
#            user_session['user_id']).fetch()
        try:
            params = {
                "user_session" : user_session,
                "user_session_object" : user_session_object,
                "user_info" : user_info,
                "user_info_object" : user_info_object,
                "userinfo_logout-url" : self.auth_config['logout_url'],
                }
            return self.render_template('secure_zone.html', **params)
        except (AttributeError, KeyError), e:
            return "Secure zone error: %s." % e


class GoogleLoginHandler(BaseHandler):

    @login_required
    def get(self):
        # Login App Engine
        user = users.get_current_user()
        try:
            #TODO: work with the logout url for jQuery Mobile
            params = {
                "nickname" : user.nickname(),
                "userinfo_logout-url" : users.create_logout_url("/"),
                }
            return self.render_template('secure_zone_google.html', **params)
        except (AttributeError, KeyError), e:
            return "Secure zone Google error: %s." % e