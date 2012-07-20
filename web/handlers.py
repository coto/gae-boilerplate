# -*- coding: utf-8 -*-

"""
	A real simple app for using webapp2 with auth and session.

	It just covers the basics. Creating a user, login, logout
	and a decorator for protecting certain handlers.

    Routes are setup in routes.py and added in main.py
"""

import models.models as models
from webapp2_extras.auth import InvalidAuthIdError
from webapp2_extras.auth import InvalidPasswordError
from webapp2_extras import security
from lib import utils
from lib import captcha
from lib.basehandler import BaseHandler
from lib.basehandler import user_required
from google.appengine.api import taskqueue
import logging
import config
import webapp2
import web.forms as forms
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from lib import twitter


class SendEmailHandler(BaseHandler):
    """
    Handler for sending Emails
    Use with TaskQueue
    """

    def post(self):
        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        utils.send_email(to, subject, body, sender)


class LoginHandler(BaseHandler):
    """
    Handler for authentication
    """

    def get(self):
        """ Returns a simple HTML form for login """

        if self.user:
            self.redirect_to('home', id=self.user_id)
        params = {
            "action": self.request.url,
            "form": self.form
        }
        return self.render_template('boilerplate_login.html', **params)

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
            password = utils.encrypt(password, config.salt)
    
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
                resend_email_uri = self.uri_for('resend-account-activation', encoded_email=utils.encode(user.email))
                message = _('Sorry, your account') + ' <strong>{0:>s}</strong>'.format(username) + " " +\
                          _('has not been activated. Please check your email to activate your account') + ". " +\
                          _('Or click') + " <a href='"+resend_email_uri+"'>" + _('this') + "</a> " + _('to resend the email')
                self.add_message(message, 'error')
                return self.redirect_to('home')

            #check twitter association in session
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
            message = _("Login invalid, Try again.") + "<br/>" + _("Don't have an account?") + \
                    '  <a href="' + self.uri_for('register') + '">' + _("Sign Up") + '</a>'
            self.add_message(message, 'error')
            return self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self.request.POST)


class SocialLoginHandler(BaseHandler):
    """
    Handler for Social authentication
    """

    def get(self, provider_name):
        callback_url = "%s/social_login/%s/complete" % (self.request.host_url, provider_name)
        if provider_name == "twitter":
            twitter_helper = twitter.TwitterAuth(self, redirect_uri=callback_url)
            self.redirect(twitter_helper.auth_url())
        else:
            message = '%s authentication is not implemented yet. ' % str(provider_name).capitalize()
            self.add_message(message,'warning')
            self.redirect_to('edit-profile')


class CallbackSocialLoginHandler(BaseHandler):
    """
    Callback (Save Information) for Social Authentication
    """

    def get(self, provider_name):
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

                    message = _('Twitter association added!')
                    self.add_message(message,'success')
                else:
                    message = _('This Twitter account is already in use!')
                    self.add_message(message,'error')
                self.redirect_to('edit-profile')
            else:
                # login with twitter
                social_user = models.SocialUser.get_by_provider_and_uid('twitter',
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
                    twitter_helper.save_association_data(user_data)
                    message = _('Account with association to your Twitter does not exist. You can associate it right now, if you login with existing site account or create new on Sign up page.')
                    self.add_message(message,'info')
                    self.redirect_to('login')
            # Debug Callback information provided
#            for k,v in user_data.items():
#                print(k +":"+  v )
        else:
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
                message = provider_name + _(' disassociated!')
                self.add_message(message,'success')
            else:
                message = _('Social account on ') + provider_name + _(' not found for this user!')
                self.add_message(message,'error')
        self.redirect_to('edit-profile')


class LogoutHandler(BaseHandler):
    """
    Destroy user session and redirect to login
    """

    def get(self):
        if self.user:
            message = _("You've signed out successfully.") # Info message
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            return _("User is logged out, but there was an error "\
                     "on the redirection.")


class RegisterHandler(BaseHandler):
    """
    Handler for Sign Up Users
    """

    def get(self):
        """ Returns a simple HTML form for create a new user """

        if self.user:
            self.redirect_to('home', id=self.user_id)
        params = {
            "action": self.request.url,
            "form": self.form
        }
        return self.render_template('boilerplate_register.html', **params)

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
        password = utils.encrypt(password, config.salt)

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=name, last_name=last_name, email=email,
            country=country, ip=self.request.remote_addr,
            activated=False,
        )

        if not user[0]: #user is a tuple
            message = _('Sorry, This user') + ' <strong>{0:>s}</strong>'.format(username) + " " +\
                      _('is already registered.')
            self.add_message(message, 'error')
            return self.redirect_to('register')
        else:
            # User registered successfully
            # But if the user registered using the form, the user has to check their email to activate the account ???
            try:
                user_info = models.User.get_by_email(email)
                if (user_info.activated == False):
                    # send email
                    subject = config.app_name + " Account Verification Email"
                    encoded_email = utils.encode(email)
                    confirmation_url = self.uri_for("account-activation",
                        encoded_email = encoded_email,
                        _full = True)
                    
                    # load email's template
                    template_val = {
                        "app_name": config.app_name,
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
                    
                    message = _('Congratulations') + ", " + str(username) + "! " + _('You are now registered') +\
                              ". " + _('Please check your email to activate your account')
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
                message = _('Welcome') + " " + str(username) + ", " + _('you are now logged in.')
                self.add_message(message, 'success')
                return self.redirect_to('home')
            except (AttributeError, KeyError), e:
                message = _('Unexpected error creating '\
                            'user') + " " + '{0:>s}.'.format(username)
                self.add_message(message, 'error')
                self.abort(403)

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.RegisterMobileForm(self.request.POST)
        else:
            return forms.RegisterForm(self.request.POST)


class AccountActivationHandler(BaseHandler):
    """
    Handler for account activation
    """

    def get(self, encoded_email):
        try:
            email = utils.decode(encoded_email)
            user = models.User.get_by_email(email)
            
            # activate the user's account
            user.activated = True
            user.put()
            
            message = _('Congratulations') + "! " + _('Your account') + " (@" + user.username + ") " +\
                _('has just been activated') + ". " + _('Please login to your account')
            self.add_message(message, "success")
            self.redirect_to('login')
            
        except (AttributeError, KeyError, InvalidAuthIdError), e:
            message = _('Unexpected error activating '\
                        'account') + " " + '{0:>s}.'.format(user.username)
            self.add_message(message, 'error')
            self.abort(403)


class ResendActivationEmailHandler(BaseHandler):
    """
    Handler to resend activation email
    """

    def get(self, encoded_email):
        try:
            email = utils.decode(encoded_email)
            user = models.User.get_by_email(email)
            
            if (user.activated == False):
                # send email
                subject = config.app_name + " Account Verification Email"
                encoded_email = utils.encode(email)
                confirmation_url = self.uri_for("account-activation",
                    encoded_email = encoded_email,
                    _full = True)
                
                # load email's template
                template_val = {
                    "app_name": config.app_name,
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
                    
                message = _('The verification email has been resent to') + " " + str(email) + ". " +\
                    _('Please check your email to activate your account')
                self.add_message(message, "success")
                return self.redirect_to('home')
            else:
                message = _('Your account has been activated') + ". " +\
                    _('Please login to your account')
                self.add_message(message, "warning")
                return self.redirect_to('home')
                
        except (KeyError, AttributeError), e:
            message = _('Sorry') + ". " + _('Some error occured') + "."
            self.add_message(message, "error")
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
            "action": self.request.url,
            "form": self.form,
            "exception" : self.request.get('exception'),
            }

        return self.render_template('boilerplate_contact.html', **params)
    
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
            subject = _("Contact")
            body = ""
            # exceptions for error pages that redirect to contact
            if exception != "":
                body = "* Exception error: %s" % exception
            body = body + """
            * IP Address: %s
            * Web Browser: %s

            * Sender name: %s
            * Sender email: %s
            * Message: %s
            """ % (remoteip, user_agent, name, email, message)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url = email_url, params={
                'to': config.contact_recipient,
                'subject' : subject,
                'body' : body,
                'sender' : config.contact_sender,
                })

            message = _('Message sent successfully.')
            self.add_message(message, 'success')
            return self.redirect_to('contact')

        except (AttributeError, KeyError), e:
            message = _('Error sending the message. Please try again later.')
            self.add_message(message, 'error')
            return self.redirect_to('contact')

    @webapp2.cached_property
    def form(self):
        return forms.ContactForm(self.request.POST)


class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit profile """

        params = {
            "action": self.request.url,
            "form": self.form
            }
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

        return self.render_template('boilerplate_edit_profile.html', **params)

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
                        message+= _('Your new username is ') + '<strong>' + username + '</strong>.'
                        
                    else:
                        message+= _('Username') + " <strong>" + username + "</strong> " + _('is already taken. It is not changed.')
                        # At least one of the values is not unique.
                        self.add_message(message,'error')
                        return self.get()
                user_info.name=name
                user_info.last_name=last_name
                user_info.country=country
                user_info.put()
                message+= " " + _('Your profile has been updated!')
                self.add_message(message,'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                message = _('Unable to update profile!')
                logging.error('Unable to update profile: ' + e)
                self.add_message(message,'error')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _('Sorry you are not logged in!')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditProfileForm(self.request.POST)


class EditPasswordHandler(BaseHandler):
    """
    Handler for Edit User Password
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for editing password """

        params = {
            "action": self.request.url,
            "form": self.form
            }
        return self.render_template('boilerplate_edit_password.html', **params)

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
            current_password = utils.encrypt(current_password, config.salt)
            try:
                user = models.User.get_by_auth_password(auth_id, current_password)
                # Password to SHA512
                password = utils.encrypt(password, config.salt)
                user.password = security.generate_password_hash(password, length=12)
                user.put()
                
                # send email
                subject = config.app_name + " Account Password Changed"

                # load email's template
                template_val = {
                    "app_name": config.app_name,
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
                    'sender' : config.contact_sender,
                    })

                #Login User
                self.auth.get_user_by_password(user.auth_ids[0], password)
                self.add_message(_('Password changed successfully'), 'success')
                return self.redirect_to('edit-profile')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Your Current Password is wrong, please try again")
                self.add_message(message, 'error')
                return self.redirect_to('edit-password')
        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in!')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.EditPasswordMobileForm(self.request.POST)
        else:
            return forms.EditPasswordForm(self.request.POST)


class EditEmailHandler(BaseHandler):
    """
    Handler for Edit User's Email
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit email """

        params = {
            "action": self.request.url,
            "form": self.form
            }
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            self.form.new_email.data = user_info.email

        return self.render_template('boilerplate_edit_email.html', **params)

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
            password = utils.encrypt(password, config.salt)
            
            try:
                # authenticate user by its password
                user = models.User.get_by_auth_password(auth_id, password)
                
                # if the user change his/her email address
                if new_email != user.email:
                    
                    # check whether the new email has been used by another user
                    aUser = models.User.get_by_email(new_email)
                    if aUser is not None:
                        message = _("The email %s is already registered." % new_email)
                        self.add_message(message, "error")
                        return self.redirect_to("edit-email")
                    
                    # send email
                    subject = config.app_name + " Email Changed Notification"
                    user_token = models.User.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for("email-changed-check", 
                        user_id = user_info.get_id(),
                        encoded_email = utils.encode(new_email),
                        token = user_token,
                        _full = True)
                    
                    # load email's template
                    template_val = {
                        "app_name": config.app_name,
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
                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': new_email,
                        'subject' : subject,
                        'body' : new_body,
                        })
                    
                    logging.error(user)
                    
                    # display successful message
                    msg = _("Please check your new email for confirmation. Your email will be updated after confirmation.")
                    self.add_message(msg, 'success')
                    return self.redirect_to('edit-profile')
                    
                else:
                    self.add_message(_("You didn't change your email"), "warning")
                    return self.redirect_to("edit-email")
                
                
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Your password is wrong, please try again")
                self.add_message(message, 'error')
                return self.redirect_to('edit-email')
                
        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in!')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditEmailForm(self.request.POST)


class PasswordResetHandler(BaseHandler):
    """
    Password Reset Handler with Captcha
    """

    reCaptcha_public_key = config.captcha_public_key
    reCaptcha_private_key = config.captcha_private_key

    def get(self):
        chtml = captcha.displayhtml(
            public_key = self.reCaptcha_public_key,
            use_ssl = False,
            error = None)
        params = {
            'action': self.request.url,
            'captchahtml': chtml,
            }
        return self.render_template('boilerplate_password_reset.html', **params)

    def post(self):
        # check captcha
        challenge = self.request.POST.get('recaptcha_challenge_field')
        response  = self.request.POST.get('recaptcha_response_field')
        remoteip  = self.request.remote_addr

        cResponse = captcha.submit(
            challenge,
            response,
            self.reCaptcha_private_key,
            remoteip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            logging.warning(cResponse.error_code)
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

        if user is not None:
            user_id = user.get_id()
            token = models.User.create_auth_token(user_id)
            email_url = self.uri_for('taskqueue-send-email')
            reset_url = self.uri_for('password-reset-check', user_id=user_id, token=token, _full=True)
            subject = _("Password reminder")
            body = _('Please click below to create a new password:') +\
                   """

                   %s
                   """ % reset_url
            taskqueue.add(url = email_url, params={
                'to': user.email,
                'subject' : subject,
                'body' : body,
                'sender' : config.contact_sender,
                })
            _message = _message + _("is associated with an account in our records, you will receive "\
                                    "an e-mail from us with instructions for resetting your password. "\
                                    "<br>If you don't receive this e-mail, please check your junk mail folder or ") +\
                       '<a href="' + self.uri_for('contact') + '">' + _('contact us') + '</a> ' +  _("for further assistance.")
            self.add_message(_message, 'success')
            return self.redirect_to('edit-profile')
        _message = _('Your email / username was not found. Please try another or ') + '<a href="' + self.uri_for('register') + '">' + _('create an account') + '</a>'
        self.add_message(_message, 'error')
        return self.redirect_to('password-reset')


class PasswordResetCompleteHandler(BaseHandler):
    """
    Handler to process the link of reset password that received the user
    """

    def get(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        params = {
            'action': self.request.url,
            'form': self.form
        }
        if verify[0] is None:
            message = _('There was an error or the link is outdated. Please copy and paste the link from your email or enter your details again below to get a new one.')
            self.add_message(message, 'warning')
            return self.redirect_to('password-reset')

        else:
            return self.render_template('boilerplate_password_reset_complete.html', **params)

    def post(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        user = verify[0]
        password = self.form.password.data.strip()
        if user and self.form.validate():
            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            user.password = security.generate_password_hash(password, length=12)
            user.put()
            # Delete token
            models.User.delete_auth_token(int(user_id), token)
            # Login User
            self.auth.get_user_by_password(user.auth_ids[0], password)
            self.add_message(_('Password changed successfully'), 'success')
            return self.redirect_to('home')

        else:
            self.add_message(_('Please correct the form errors.'), 'error')
            return self.redirect_to('password-reset-check', user_id=user_id, token=token)

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.PasswordResetCompleteMobileForm(self.request.POST)
        else:
            return forms.PasswordResetCompleteForm(self.request.POST)


class EmailChangedCompleteHandler(BaseHandler):
    """
    Handler for completed email change
    Will be called when the user click confirmation link from email
    """

    def get(self, user_id, encoded_email, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        email = utils.decode(encoded_email)
        if verify[0] is None:
            self.add_message('There was an error or the link is outdated. Please copy and paste the link from your email.', 'warning')
            self.redirect_to('home')

        else:
            # save new email
            user = verify[0]
            user.email = email
            user.put()
            # delete token
            models.User.delete_auth_token(int(user_id), token)
            # add successful message and redirect
            self.add_message("Your email has been successfully updated!", "success")
            self.redirect_to('edit-profile')


class SecureRequestHandler(BaseHandler):
    """
    Only accessible to users that are logged in
    """

    @user_required
    def get(self, **kwargs):
        user_session = self.user
        user_session_object = self.auth.store.get_session(self.request)

        user_info = models.User.get_by_id(long( self.user_id ))
        user_info_object = self.auth.store.user_model.get_by_auth_token(
            user_session['user_id'], user_session['token'])

        try:
            params = {
                "user_session" : user_session,
                "user_session_object" : user_session_object,
                "user_info" : user_info,
                "user_info_object" : user_info_object,
                "userinfo_logout-url" : self.auth_config['logout_url'],
                }
            return self.render_template('boilerplate_secure_zone.html', **params)
        except (AttributeError, KeyError), e:
            return _("Secure zone error:") + " %s." % e


class HomeRequestHandler(BaseHandler):
    """
    Handler to show the home page
    """

    def get(self):
        """ Returns a simple HTML form for home """
        params = {}
        return self.render_template('boilerplate_home.html', **params)


