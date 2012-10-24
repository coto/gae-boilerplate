# -*- coding: utf-8 -*-

"""
    A real simple app for using webapp2 with auth and session.

    It just covers the basics. Creating a user, login, logout
    and a decorator for protecting certain handlers.

    Routes are setup in routes.py and added in main.py
"""
# standard library imports
import logging
import re
import json

# related third party imports
import webapp2
import httpagentparser
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from google.appengine.api import taskqueue
from linkedin import linkedin

# local application/library specific imports
import models
import forms as forms
from lib import utils, captcha, twitter
from lib.basehandler import BaseHandler
from lib.basehandler import user_required
from lib import facebook


class RegisterBaseHandler(BaseHandler):
    """
    Base class for handlers with registration and login forms.
    """
    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.RegisterMobileForm(self)
        else:
            return forms.RegisterForm(self)


class SendEmailHandler(BaseHandler):
    """
    Core Handler for sending Emails
    Use with TaskQueue
    """
    def post(self):

        from google.appengine.api import mail, app_identity
        from google.appengine.api.datastore_errors import BadValueError
        from google.appengine.runtime import apiproxy_errors

        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        if sender != '' or not utils.is_email_valid(sender):
            if utils.is_email_valid(self.app.config.get('contact_sender')):
                sender = self.app.config.get('contact_sender')
            else:
                app_id = app_identity.get_application_id()
                sender = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)

        try:
            logEmail = models.LogEmail(
                sender = sender,
                to = to,
                subject = subject,
                body = body,
                when = utils.get_date_time("datetimeProperty")
            )
            logEmail.put()
        except (apiproxy_errors.OverQuotaError, BadValueError):
            logging.error("Error saving Email Log in datastore")

        message = mail.EmailMessage()
        message.sender=sender
        message.to=to
        message.subject=subject
        message.html=body
        message.send()


class LoginHandler(BaseHandler):
    """
    Handler for authentication
    """

    def get(self):
        """ Returns a simple HTML form for login """

        if self.user:
            self.redirect_to('home')
        params = {}
        return self.render_template('login.html', **params)

    def post(self):
        """
        username: Get the username from POST dict
        password: Get the password from POST dict
        """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()

        try:
            if utils.is_email_valid(username):
                user = models.User.get_by_email(username)
                if user:
                    auth_id = user.auth_ids[0]
                else:
                    raise InvalidAuthIdError
            else:
                auth_id = "own:%s" % username
                user = models.User.get_by_auth_id(auth_id)

            password = self.form.password.data.strip()
            remember_me = True if str(self.request.POST.get('remember_me')) == 'on' else False

            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            # Try to login user with password
            # Raises InvalidAuthIdError if user is not found
            # Raises InvalidPasswordError if provided password
            # doesn't match with specified user
            self.auth.get_user_by_password(
                auth_id, password, remember=remember_me)

            # if user account is not activated, logout and redirect to home
            if (user.activated == False):
                # logout
                self.auth.unset_session()

                # redirect to home with error message
                resend_email_uri = self.uri_for('resend-account-activation', user_id=user.get_id(),
                                                token=models.User.create_resend_token(user.get_id()))
                message = _('Your account has not yet been activated. Please check your email to activate it or') +\
                          ' <a href="'+resend_email_uri+'">' + _('click here') + '</a> ' + _('to resend the email.')
                self.add_message(message, 'error')
                return self.redirect_to('home')

            # check twitter association in session
            twitter_helper = twitter.TwitterAuth(self)
            twitter_association_data = twitter_helper.get_association_data()
            if twitter_association_data is not None:
                if models.SocialUser.check_unique(user.key, 'twitter', str(twitter_association_data['id'])):
                    social_user = models.SocialUser(
                        user = user.key,
                        provider = 'twitter',
                        uid = str(twitter_association_data['id']),
                        extra_data = twitter_association_data
                    )
                    social_user.put()

            # check facebook association
            fb_data = None
            try:
                fb_data = json.loads(self.session['facebook'])
            except:
                pass

            if fb_data is not None:
                if models.SocialUser.check_unique(user.key, 'facebook', str(fb_data['id'])):
                    social_user = models.SocialUser(
                        user = user.key,
                        provider = 'facebook',
                        uid = str(fb_data['id']),
                        extra_data = fb_data
                    )
                    social_user.put()

            # check linkedin association
            li_data = None
            try:
                li_data = json.loads(self.session['linkedin'])
            except:
                pass
            if li_data is not None:
                if models.SocialUser.check_unique(user.key, 'linkedin', str(li_data['id'])):
                    social_user = models.SocialUser(
                        user = user.key,
                        provider = 'linkedin',
                        uid = str(li_data['id']),
                        extra_data = li_data
                    )
                    social_user.put()

            # end linkedin

            logVisit = models.LogVisit(
                user=user.key,
                uastring=self.request.user_agent,
                ip=self.request.remote_addr,
                timestamp=utils.get_date_time()
            )
            logVisit.put()
            self.redirect_to('home')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            message = _("Your username or password is incorrect. "
                        "Please try again (make sure your caps lock is off)")
            self.add_message(message, 'error')
            return self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self)


class SocialLoginHandler(BaseHandler):
    """
    Handler for Social authentication
    """

    def get(self, provider_name):
        provider_display_name = models.SocialUser.PROVIDERS_INFO[provider_name]['label']

        if not self.app.config.get('enable_federated_login'):
            message = _('Federated login is disabled.')
            self.add_message(message, 'warning')
            return self.redirect_to('login')
        callback_url = "%s/social_login/%s/complete" % (self.request.host_url, provider_name)

        if provider_name == "twitter":
            twitter_helper = twitter.TwitterAuth(self, redirect_uri=callback_url)
            self.redirect(twitter_helper.auth_url())

        elif provider_name == "facebook":
            self.session['linkedin'] = None
            perms = ['email', 'publish_stream']
            self.redirect(facebook.auth_url(self.app.config.get('fb_api_key'), callback_url, perms))

        elif provider_name == 'linkedin':
            self.session['facebook'] = None
            link = linkedin.LinkedIn(self.app.config.get('linkedin_api'), self.app.config.get('linkedin_secret'), callback_url)
            if link.request_token():
                self.session['request_token']=link._request_token
                self.session['request_token_secret']=link._request_token_secret
                self.redirect(link.get_authorize_url())

        else:
            message = _('%s authentication is not yet implemented.' % provider_display_name)
            self.add_message(message, 'warning')
            self.redirect_to('edit-profile')


class CallbackSocialLoginHandler(BaseHandler):
    """
    Callback (Save Information) for Social Authentication
    """

    def get(self, provider_name):
        if not self.app.config.get('enable_federated_login'):
            message = _('Federated login is disabled.')
            self.add_message(message, 'warning')
            return self.redirect_to('login')
        if provider_name == "twitter":
            oauth_token = self.request.get('oauth_token')
            oauth_verifier = self.request.get('oauth_verifier')
            twitter_helper = twitter.TwitterAuth(self)
            user_data = twitter_helper.auth_complete(oauth_token,
                oauth_verifier)
            if self.user:
                # new association with twitter
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, 'twitter', str(user_data['id'])):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = 'twitter',
                        uid = str(user_data['id']),
                        extra_data = user_data
                    )
                    social_user.put()

                    message = _('Twitter association added.')
                    self.add_message(message, 'success')
                else:
                    message = _('This Twitter account is already in use.')
                    self.add_message(message, 'error')
                self.redirect_to('edit-profile')
            else:
                # login with twitter
                social_user = models.SocialUser.get_by_provider_and_uid('twitter',
                    str(user_data['user_id']))
                if social_user:
                    # Social user exists. Need authenticate related site account
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exists. Need show login and registration forms
                    twitter_helper.save_association_data(user_data)
                    message = _('This Twitter account is not associated with any local account. '
                                'If you already have a %s Account, you have <a href="/login/">sign in here</a> '
                                'or <a href="/register/">create an account</a>.' % self.app.config.get('app_name'))
                    self.add_message(message, 'warning')
                    self.redirect_to('login')

        # facebook association
        elif provider_name == "facebook":
            code = self.request.get('code')
            token = facebook.get_access_token_from_code(code, callback_url, config.facebook_app_key, config.facebook_app_secret)
            callback_url = "%s/social_login/%s/complete" % (self.request.host_url, provider_name)
            token = facebook.get_access_token_from_code(code, callback_url, self.app.config.get('fb_api_key'), self.app.config.get('fb_secret'))
            access_token = token['access_token']
            fb = facebook.GraphAPI(access_token)
            user_data = fb.get_object('me')
            if self.user:
                # new association with facebook
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, 'facebook', str(user_data['id'])):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = 'facebook',
                        uid = str(user_data['id']),
                        extra_data = user_data
                    )
                    social_user.put()

                    message = _('Facebook association added!')
                    self.add_message(message,'success')
                else:
                    message = _('This Facebook account is already in use!')
                    self.add_message(message,'error')
                self.redirect_to('edit-profile')
            else:
                # login with Facebook
                social_user = models.SocialUser.get_by_provider_and_uid('facebook',
                    str(user_data['id']))
                if social_user:
                    # Social user exists. Need authenticate related site account
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exists. Need show login and registration forms

                    self.session['facebook']=json.dumps(user_data)
                    login_url = '%s/login/'  % self.request.host_url
                    signup_url = '%s/register/' %  self.request.host_url
                    message = _('The Facebook account isn\'t associated with any local account. If you already have a Google App Engine Boilerplate Account, you have <a href="%s">sign in here</a> or <a href="%s">Create an account</a>') % (login_url, signup_url)
                    self.add_message(message,'info')
                    self.redirect_to('login')

            # end facebook
         # association with linkedin
        elif provider_name == "linkedin":
            callback_url = "%s/social_login/%s/complete" % (self.request.host_url, provider_name)
            link = linkedin.LinkedIn(self.app.config.get('linkedin_api'), self.app.config.get('linkedin_secret'), callback_url)
            request_token = self.session['request_token']
            request_token_secret= self.session['request_token_secret']
            link._request_token = request_token
            link._request_token_secret = request_token_secret
            verifier = self.request.get('oauth_verifier')
            #~ print 'test'
            #~ print 'request_token= %s ; request_token_secret= %s ;verifier = %s ' % (request_token, request_token_secret, verifier)
            link.access_token(verifier=verifier)
            u_data = link.get_profile()
            user_key = re.search(r'key=(\d+)', u_data.private_url).group(1)
            user_data={'first_name':u_data.first_name, 'last_name':u_data.last_name ,'id':user_key}
            self.session['linkedin'] = json.dumps(user_data)

            if self.user:
                # new association with linkedin
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, 'linkedin', str(user_data['id'])):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = 'linkedin',
                        uid = str(user_data['id']),
                        extra_data = user_data
                    )
                    social_user.put()

                    message = _('Linkedin association added!')
                    self.add_message(message,'success')
                else:
                    message = _('This Linkedin account is already in use!')
                    self.add_message(message,'error')
                self.redirect_to('edit-profile')
            else:
                # login with Linkedin
                social_user = models.SocialUser.get_by_provider_and_uid('linkedin',
                    str(user_data['id']))
                if social_user:
                    # Social user exists. Need authenticate related site account
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exists. Need show login and registration forms
                    self.session['linkedin'] = json.dumps(user_data)
                    login_url = '%s/login/'  % self.request.host_url
                    signup_url = '%s/register/' %  self.request.host_url
                    message = _('The Linkedin account isn\'t associated with any local account. If you already have a Google App Engine Boilerplate Account, you have <a href="%s">sign in here</a> or <a href="%s">Create an account</a>') % (login_url, signup_url)
                    self.add_message(message,'info')
                    self.redirect_to('login')

            #end linkedin

        # google, myopenid, yahoo OpenID Providers
        elif provider_name in models.SocialUser.open_id_providers():
            provider_display_name = models.SocialUser.PROVIDERS_INFO[provider_name]['label']
            # get info passed from OpenId Provider
            from google.appengine.api import users
            current_user = users.get_current_user()
            if current_user:
                if current_user.federated_identity():
                    uid = current_user.federated_identity()
                else:
                    uid = current_user.user_id()
                email = current_user.email()
            else:
                message = _('No user authentication information received from %s. '
                            'Please ensure you are logging in from an authorized OpenID Provider (OP).'
                            % provider_display_name)
                self.add_message(message, 'error')
                return self.redirect_to('login')
            if self.user:
                # add social account to user
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, provider_name, uid):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = provider_name,
                        uid = uid
                    )
                    social_user.put()

                    message = _('%s association successfully added.' % provider_display_name)
                    self.add_message(message, 'success')
                else:
                    message = _('This %s account is already in use.' % provider_display_name)
                    self.add_message(message, 'error')
                self.redirect_to('edit-profile')
            else:
                # login with OpenId Provider
                social_user = models.SocialUser.get_by_provider_and_uid(provider_name, uid)
                if social_user:
                    # Social user found. Authenticate the user
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exist yet so create it with the federated identity provided (uid)
                    # and create prerequisite user and log the user account in
                    if models.SocialUser.check_unique_uid(provider_name, uid):
                        # create user
                        # Returns a tuple, where first value is BOOL.
                        # If True ok, If False no new user is created
                        # Assume provider has already verified email address
                        # if email is provided so set activated to True
                        auth_id = "%s:%s" % (provider_name, uid)
                        if email:
                            unique_properties = ['email']
                            user_info = self.auth.store.user_model.create_user(
                                auth_id, unique_properties, email=email,
                                activated=True
                            )
                        else:
                            user_info = self.auth.store.user_model.create_user(
                                auth_id, activated=True
                            )
                        if not user_info[0]: #user is a tuple
                            message = _('The account %s is already in use.' % provider_display_name)
                            self.add_message(message, 'error')
                            return self.redirect_to('register')

                        user = user_info[1]

                        # create social user and associate with user
                        social_user = models.SocialUser(
                            user = user.key,
                            provider = provider_name,
                            uid = uid
                        )
                        social_user.put()
                        # authenticate user
                        self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                        logVisit = models.LogVisit(
                            user = user.key,
                            uastring = self.request.user_agent,
                            ip = self.request.remote_addr,
                            timestamp = utils.get_date_time()
                        )
                        logVisit.put()

                        message = _('%s association successfully added.' % provider_display_name)
                        self.add_message(message, 'success')
                        self.redirect_to('home')
                    else:
                        message = _('This %s account is already in use.' % provider_display_name)
                        self.add_message(message, 'error')
        else:
            message = _('This authentication method is not yet implemented.')
            self.add_message(message, 'warning')
            self.redirect_to('login')


class DeleteSocialProviderHandler(BaseHandler):
    """
    Delete Social association with an account
    """

    @user_required
    def get(self, provider_name):
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            social_user = models.SocialUser.get_by_user_and_provider(user_info.key, provider_name)
            if social_user:
                social_user.key.delete()
                message = _('%s successfully disassociated.' % provider_name)
                self.add_message(message, 'success')
            else:
                message = _('Social account on %s not found for this user.' % provider_name)
                self.add_message(message, 'error')
        self.redirect_to('edit-profile')


class LogoutHandler(BaseHandler):
    """
    Destroy user session and redirect to login
    """

    def get(self):
        if self.user:
            message = _("You've signed out successfully. Warning: Please clear all cookies and logout "
                        "of OpenId providers too if you logged in on a public computer.")
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            logging.error("Error logging out: %s" % e)
            message = _("User is logged out, but there was an error on the redirection.")
            self.add_message(message, 'error')
            return self.redirect_to('home')


class RegisterHandler(RegisterBaseHandler):
    """
    Handler for Sign Up Users
    """

    def get(self):
        """ Returns a simple HTML form for create a new user """

        if self.user:
            self.redirect_to('home')
        params = {}
        return self.render_template('register.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        email = self.form.email.data.lower()
        password = self.form.password.data.strip()
        country = self.form.country.data

        # Password to SHA512
        password = utils.hashing(password, self.app.config.get('salt'))

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            ip=self.request.remote_addr, country=country
        )

        if not user[0]: #user is a tuple
            if "username" in str(user[1]):
                message = _('Sorry, The username %s is already registered.' % '<strong>{0:>s}</strong>'.format(username) )
            elif "email" in str(user[1]):
                message = _('Sorry, The email %s is already registered.' % '<strong>{0:>s}</strong>'.format(email) )
            else:
                message = _('Sorry, The user is already registered.')
            self.add_message(message, 'error')
            return self.redirect_to('register')
        else:
            # User registered successfully
            # But if the user registered using the form, the user has to check their email to activate the account ???
            try:
                user_info = models.User.get_by_email(email)
                if (user_info.activated == False):
                    # send email
                    subject =  _("%s Account Verification" % self.app.config.get('app_name'))
                    confirmation_url = self.uri_for("account-activation",
                        user_id=user_info.get_id(),
                        token = models.User.create_auth_token(user_info.get_id()),
                        _full = True)

                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "username": username,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }
                    body_path = "emails/account_activation.txt"
                    body = self.jinja2.render_template(body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': str(email),
                        'subject' : subject,
                        'body' : body,
                        })

                    message = _('You were successfully registered. '
                                'Please check your email to activate your account.')
                    self.add_message(message, 'success')
                    return self.redirect_to('home')

                # If the user didn't register using registration form ???
                db_user = self.auth.get_user_by_password(user[1].auth_ids[0], password)
                # Check twitter association in session
                twitter_helper = twitter.TwitterAuth(self)
                twitter_association_data = twitter_helper.get_association_data()
                if twitter_association_data is not None:
                    if models.SocialUser.check_unique(user[1].key, 'twitter', str(twitter_association_data['id'])):
                        social_user = models.SocialUser(
                            user = user[1].key,
                            provider = 'twitter',
                            uid = str(twitter_association_data['id']),
                            extra_data = twitter_association_data
                        )
                        social_user.put()

                #check facebook association
                fb_data = json.loads(self.session['facebook'])

                if fb_data is not None:
                    if models.SocialUser.check_unique(user.key, 'facebook', str(fb_data['id'])):
                        social_user = models.SocialUser(
                            user = user.key,
                            provider = 'facebook',
                            uid = str(fb_data['id']),
                            extra_data = fb_data
                        )
                        social_user.put()
                #check linkedin association
                li_data = json.loads(self.session['linkedin'])
                if li_data is not None:
                    if models.SocialUser.check_unique(user.key, 'linkedin', str(li_data['id'])):
                        social_user = models.SocialUser(
                            user = user.key,
                            provider = 'linkedin',
                            uid = str(li_data['id']),
                            extra_data = li_data
                        )
                        social_user.put()


                message = _('Welcome %s, you are now logged in.' % '<strong>{0:>s}</strong>'.format(username) )
                self.add_message(message, 'success')
                return self.redirect_to('home')
            except (AttributeError, KeyError), e:
                logging.error('Unexpected error creating the user %s: %s' % (username, e ))
                message = _('Unexpected error creating the user %s' % username )
                self.add_message(message, 'error')
                return self.redirect_to('home')


class AccountActivationHandler(BaseHandler):
    """
    Handler for account activation
    """

    def get(self, user_id, token):
        try:
            if not models.User.validate_auth_token(user_id, token):
                message = _('The link is invalid.')
                self.add_message(message, 'error')
                return self.redirect_to('home')

            user = models.User.get_by_id(long(user_id))
            # activate the user's account
            user.activated = True
            user.put()

            # Login User
            self.auth.get_user_by_token(int(user_id), token)

            # Delete token
            models.User.delete_auth_token(user_id, token)

            message = _('Congratulations, Your account %s has been successfully activated.'
                        % '<strong>{0:>s}</strong>'.format(user.username) )
            self.add_message(message, 'success')
            self.redirect_to('home')

        except (AttributeError, KeyError, InvalidAuthIdError, NameError), e:
            logging.error("Error activating an account: %s" % e)
            message = _('Sorry, Some error occurred.')
            self.add_message(message, 'error')
            return self.redirect_to('home')


class ResendActivationEmailHandler(BaseHandler):
    """
    Handler to resend activation email
    """

    def get(self, user_id, token):
        try:
            if not models.User.validate_resend_token(user_id, token):
                message = _('The link is invalid.')
                self.add_message(message, 'error')
                return self.redirect_to('home')

            user = models.User.get_by_id(long(user_id))
            email = user.email

            if (user.activated == False):
                # send email
                subject = _("%s Account Verification" % self.app.config.get('app_name'))
                confirmation_url = self.uri_for("account-activation",
                    user_id = user.get_id(),
                    token = models.User.create_auth_token(user.get_id()),
                    _full = True)

                # load email's template
                template_val = {
                    "app_name": self.app.config.get('app_name'),
                    "username": user.username,
                    "confirmation_url": confirmation_url,
                    "support_url": self.uri_for("contact", _full=True)
                }
                body_path = "emails/account_activation.txt"
                body = self.jinja2.render_template(body_path, **template_val)

                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url = email_url, params={
                    'to': str(email),
                    'subject' : subject,
                    'body' : body,
                    })

                models.User.delete_resend_token(user_id, token)

                message = _('The verification email has been resent to %s. '
                            'Please check your email to activate your account.' % email)
                self.add_message(message, 'success')
                return self.redirect_to('home')
            else:
                message = _('Your account has been activated. Please <a href="/login/">sign in</a> to your account.')
                self.add_message(message, 'warning')
                return self.redirect_to('home')

        except (KeyError, AttributeError), e:
            logging.error("Error resending activation email: %s" % e)
            message = _('Sorry, Some error occurred.')
            self.add_message(message, 'error')
            return self.redirect_to('home')


class ContactHandler(BaseHandler):
    """
    Handler for Contact Form
    """

    def get(self):
        """ Returns a simple HTML for contact form """

        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            if user_info.name or user_info.last_name:
                self.form.name.data = user_info.name + " " + user_info.last_name
            if user_info.email:
                self.form.email.data = user_info.email
        params = {
            "exception" : self.request.get('exception')
            }

        return self.render_template('contact.html', **params)

    def post(self):
        """ validate contact form """

        if not self.form.validate():
            return self.get()
        remoteip  = self.request.remote_addr
        user_agent  = self.request.user_agent
        exception = self.request.POST.get('exception')
        name = self.form.name.data.strip()
        email = self.form.email.data.lower()
        message = self.form.message.data.strip()

        try:
            # parsing user_agent and getting which os key to use
            # windows uses 'os' while other os use 'flavor'
            logging.info(user_agent)
            ua = httpagentparser.detect(user_agent)
            os = ua.has_key('flavor') and 'flavor' or 'os'

            operating_system_full_name = str(ua[os]['name'])

            if 'version' in ua[os]:
                operating_system_full_name += ' '+str(ua[os]['version'])

            if 'dist' in ua:
                operating_system_full_name += ' '+str(ua['dist'])

            template_val = {
                "name": name,
                "email": email,
                "browser": str(ua['browser']['name']),
                "browser_version": str(ua['browser']['version']),
                "operating_system": operating_system_full_name,
                "ip": remoteip,
                "message": message
            }
        except Exception as e:
            logging.error("error getting user agent info: %s" % e)

        try:
            subject = _("Contact")
            # exceptions for error pages that redirect to contact
            if exception != "":
                subject = subject + " (Exception error: %s)" % exception

            body_path = "emails/contact.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url = email_url, params={
                'to': self.app.config.get('contact_recipient'),
                'subject' : subject,
                'body' : body,
                'sender' : self.app.config.get('contact_sender'),
                })

            message = _('Your message was sent successfully.')
            self.add_message(message, 'success')
            return self.redirect_to('contact')

        except (AttributeError, KeyError), e:
            logging.error('Error sending contact form: %s' % e)
            message = _('Error sending the message. Please try again later.')
            self.add_message(message, 'error')
            return self.redirect_to('contact')

    @webapp2.cached_property
    def form(self):
        return forms.ContactForm(self)


class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit profile """

        params = {}
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            self.form.username.data = user_info.username
            self.form.name.data = user_info.name
            self.form.last_name.data = user_info.last_name
            self.form.country.data = user_info.country
            providers_info = user_info.get_social_providers_info()
            params['used_providers'] = providers_info['used']
            params['unused_providers'] = providers_info['unused']
            params['country'] = user_info.country

        return self.render_template('edit_profile.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        country = self.form.country.data

        try:
            user_info = models.User.get_by_id(long(self.user_id))

            try:
                message=''
                # update username if it has changed and it isn't already taken
                if username != user_info.username:
                    user_info.unique_properties = ['username','email']
                    uniques = [
                               'User.username:%s' % username,
                               'User.auth_id:own:%s' % username,
                               ]
                    # Create the unique username and auth_id.
                    success, existing = Unique.create_multi(uniques)
                    if success:
                        # free old uniques
                        Unique.delete_multi(['User.username:%s' % user_info.username, 'User.auth_id:own:%s' % user_info.username])
                        # The unique values were created, so we can save the user.
                        user_info.username=username
                        user_info.auth_ids[0]='own:%s' % username
                        message+= _('Your new username is %s' % '<strong>{0:>s}</strong>'.format(username) )

                    else:
                        message+= _('The username %s is already taken. Please choose another.'
                                % '<strong>{0:>s}</strong>'.format(username) )
                        # At least one of the values is not unique.
                        self.add_message(message, 'error')
                        return self.get()
                user_info.name=name
                user_info.last_name=last_name
                user_info.country=country
                user_info.put()
                message+= " " + _('Thanks, your settings have been saved.')
                self.add_message(message, 'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating profile: ' + e)
                message = _('Unable to update profile. Please try again later.')
                self.add_message(message, 'error')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _('Sorry you are not logged in.')
            self.add_message(login_error_message, 'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditProfileForm(self)


class EditPasswordHandler(BaseHandler):
    """
    Handler for Edit User Password
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for editing password """

        params = {}
        return self.render_template('edit_password.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        current_password = self.form.current_password.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username

            # Password to SHA512
            current_password = utils.hashing(current_password, self.app.config.get('salt'))
            try:
                user = models.User.get_by_auth_password(auth_id, current_password)
                # Password to SHA512
                password = utils.hashing(password, self.app.config.get('salt'))
                user.password = security.generate_password_hash(password, length=12)
                user.put()

                # send email
                subject = self.app.config.get('app_name') + " Account Password Changed"

                # load email's template
                template_val = {
                    "app_name": self.app.config.get('app_name'),
                    "first_name": user.name,
                    "username": user.username,
                    "email": user.email,
                    "reset_password_url": self.uri_for("password-reset", _full=True)
                }
                email_body_path = "emails/password_changed.txt"
                email_body = self.jinja2.render_template(email_body_path, **template_val)
                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url = email_url, params={
                    'to': user.email,
                    'subject' : subject,
                    'body' : email_body,
                    'sender' : self.app.config.get('contact_sender'),
                    })

                #Login User
                self.auth.get_user_by_password(user.auth_ids[0], password)
                self.add_message(_('Password changed successfully.'), 'success')
                return self.redirect_to('edit-profile')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Incorrect password! Please enter your current password to change your account settings.")
                self.add_message(message, 'error')
                return self.redirect_to('edit-password')
        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in.')
            self.add_message(login_error_message, 'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.EditPasswordMobileForm(self)
        else:
            return forms.EditPasswordForm(self)


class EditEmailHandler(BaseHandler):
    """
    Handler for Edit User's Email
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit email """

        params = {}
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            params['current_email'] = user_info.email

        return self.render_template('edit_email.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        new_email = self.form.new_email.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username
            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            try:
                # authenticate user by its password
                user = models.User.get_by_auth_password(auth_id, password)

                # if the user change his/her email address
                if new_email != user.email:

                    # check whether the new email has been used by another user
                    aUser = models.User.get_by_email(new_email)
                    if aUser is not None:
                        message = _("The email %s is already registered." % new_email)
                        self.add_message(message, 'error')
                        return self.redirect_to("edit-email")

                    # send email
                    subject = _("%s Email Changed Notification" % self.app.config.get('app_name'))
                    user_token = models.User.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for("email-changed-check",
                        user_id = user_info.get_id(),
                        encoded_email = utils.encode(new_email),
                        token = user_token,
                        _full = True)

                    # load email's template
                    template_val = {
                        "app_name": self.app.config.get('app_name'),
                        "first_name": user.name,
                        "username": user.username,
                        "new_email": new_email,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }

                    old_body_path = "emails/email_changed_notification_old.txt"
                    old_body = self.jinja2.render_template(old_body_path, **template_val)

                    new_body_path = "emails/email_changed_notification_new.txt"
                    new_body = self.jinja2.render_template(new_body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': user.email,
                        'subject' : subject,
                        'body' : old_body,
                        })
                    taskqueue.add(url = email_url, params={
                        'to': new_email,
                        'subject' : subject,
                        'body' : new_body,
                        })

                    # display successful message
                    msg = _("Please check your new email for confirmation. Your email will be updated after confirmation.")
                    self.add_message(msg, 'success')
                    return self.redirect_to('edit-profile')

                else:
                    self.add_message(_("You didn't change your email."), "warning")
                    return self.redirect_to("edit-email")


            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Incorrect password! Please enter your current password to change your account settings.")
                self.add_message(message, 'error')
                return self.redirect_to('edit-email')

        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in.')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditEmailForm(self)


class PasswordResetHandler(BaseHandler):
    """
    Password Reset Handler with Captcha
    """



    def get(self):
        chtml = captcha.displayhtml(
            public_key = self.app.config.get('captcha_public_key'),
            use_ssl = False,
            error = None)
        if self.app.config.get('captcha_public_key') == "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE" or \
           self.app.config.get('captcha_private_key') == "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE":
            chtml = '<div class="alert alert-error"><strong>Error</strong>: You have to ' \
                    '<a href="http://www.google.com/recaptcha/whyrecaptcha" target="_blank">sign up ' \
                    'for API keys</a> in order to use reCAPTCHA.</div>' \
                    '<input type="hidden" name="recaptcha_challenge_field" value="manual_challenge" />' \
                    '<input type="hidden" name="recaptcha_response_field" value="manual_challenge" />'
        params = {
            'captchahtml': chtml,
            }
        return self.render_template('password_reset.html', **params)

    def post(self):
        # check captcha
        challenge = self.request.POST.get('recaptcha_challenge_field')
        response  = self.request.POST.get('recaptcha_response_field')
        remoteip  = self.request.remote_addr

        cResponse = captcha.submit(
            challenge,
            response,
            self.app.config.get('captcha_private_key'),
            remoteip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _('Wrong image verification code. Please try again.')
            self.add_message(_message, 'error')
            return self.redirect_to('password-reset')
            #check if we got an email or username
        email_or_username = str(self.request.POST.get('email_or_username')).lower().strip()
        if utils.is_email_valid(email_or_username):
            user = models.User.get_by_email(email_or_username)
            _message = _("If the e-mail address you entered") + " (<strong>%s</strong>) " % email_or_username
        else:
            auth_id = "own:%s" % email_or_username
            user = models.User.get_by_auth_id(auth_id)
            _message = _("If the username you entered") + " (<strong>%s</strong>) " % email_or_username

        _message = _message + _("is associated with an account in our records, you will receive "
                                "an e-mail from us with instructions for resetting your password. "
                                "<br>If you don't receive instructions within a minute or two, "
                                "check your email's spam and junk filters, or ") +\
                   '<a href="' + self.uri_for('contact') + '">' + _('contact us') + '</a> ' +  _("for further assistance.")

        if user is not None:
            user_id = user.get_id()
            token = models.User.create_auth_token(user_id)
            email_url = self.uri_for('taskqueue-send-email')
            reset_url = self.uri_for('password-reset-check', user_id=user_id, token=token, _full=True)
            subject = _("%s Password Assistance" % self.app.config.get('app_name'))

            # load email's template
            template_val = {
                "username": user.username,
                "email": user.email,
                "reset_password_url": reset_url,
                "support_url": self.uri_for("contact", _full=True),
                "app_name": self.app.config.get('app_name'),
            }

            body_path = "emails/reset_password.txt"
            body = self.jinja2.render_template(body_path, **template_val)
            taskqueue.add(url = email_url, params={
                'to': user.email,
                'subject' : subject,
                'body' : body,
                'sender' : self.app.config.get('contact_sender'),
                })
        self.add_message(_message, 'warning')
        return self.redirect_to('login')


class PasswordResetCompleteHandler(BaseHandler):
    """
    Handler to process the link of reset password that received the user
    """

    def get(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        params = {}
        if verify[0] is None:
            message = _('The URL you tried to use is either incorrect or no longer valid. '
                        'Enter your details again below to get a new one.')
            self.add_message(message, 'warning')
            return self.redirect_to('password-reset')

        else:
            return self.render_template('password_reset_complete.html', **params)

    def post(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        user = verify[0]
        password = self.form.password.data.strip()
        if user and self.form.validate():
            # Password to SHA512
            password = utils.hashing(password, self.app.config.get('salt'))

            user.password = security.generate_password_hash(password, length=12)
            user.put()
            # Delete token
            models.User.delete_auth_token(int(user_id), token)
            # Login User
            self.auth.get_user_by_password(user.auth_ids[0], password)
            self.add_message(_('Password changed successfully.'), 'success')
            return self.redirect_to('home')

        else:
            self.add_message(_('The two passwords must match.'), 'error')
            return self.redirect_to('password-reset-check', user_id=user_id, token=token)

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.PasswordResetCompleteMobileForm(self)
        else:
            return forms.PasswordResetCompleteForm(self)


class EmailChangedCompleteHandler(BaseHandler):
    """
    Handler for completed email change
    Will be called when the user click confirmation link from email
    """

    def get(self, user_id, encoded_email, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        email = utils.decode(encoded_email)
        if verify[0] is None:
            message = _('The URL you tried to use is either incorrect or no longer valid.')
            self.add_message(message, 'warning')
            self.redirect_to('home')

        else:
            # save new email
            user = verify[0]
            user.email = email
            user.put()
            # delete token
            models.User.delete_auth_token(int(user_id), token)
            # add successful message and redirect
            message = _('Your email has been successfully updated.')
            self.add_message(message, 'success')
            self.redirect_to('edit-profile')


class HomeRequestHandler(RegisterBaseHandler):
    """
    Handler to show the home page
    """

    def get(self):
        """ Returns a simple HTML form for home """
        params = {}
        return self.render_template('home.html', **params)
