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
from google.appengine.api import mail
from google.appengine.api import app_identity
import logging
import config
import webapp2
import web.forms as forms


class BootstrapHandler(BaseHandler):

    def get(self):
        """
              Returns a simple HTML form for home
        """
        params = {}
        return self.render_template('boilerplate_bootstrap.html', **params)


class HomeRequestHandler(BaseHandler):

    def get(self):
        """
              Returns a simple HTML form for home
        """
        params = {}
        return self.render_template('boilerplate_home.html', **params)


class PasswordResetHandler(BaseHandler):
    """
    Password Reset Handler with Captcha
    """
    reCaptcha_public_key = config.captcha_public_key
    reCaptcha_private_key = config.captcha_private_key
    
    def get(self):
        if self.user:
            self.redirect_to('secure')
        
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
            _message = 'Wrong image verification code. Please try again.'
            self.add_message(_message, 'error')
            return self.redirect_to('password-reset')
        #check if we got an email or username
        email_or_username = str(self.request.POST.get('email_or_username')).lower().strip()
        if utils.is_email_valid(email_or_username):
            user = models.User.get_by_email(email_or_username)
            _message = "If the e-mail address you entered <strong>%s</strong> " % email_or_username
        else:
            auth_id = "own:%s" % email_or_username
            user = models.User.get_by_auth_id(auth_id)
            _message = "If the username you entered <strong>%s</strong> " % email_or_username

        if user is not None:
            user_id = user.get_id()
            token = models.User.create_auth_token(user_id)
            email_send_url = self.uri_for('send-reset-email')
            taskqueue.add(url = email_send_url, params={
                'recipient_email': user.email,
                'token' : token,
                'user_id' : user_id,
                })
            _message = _message + "is associated with an account in our records, you will receive " \
                       "an e-mail from us with instructions for resetting your password. " \
                       "<br>If you don't receive this e-mail, please check your junk mail folder or " \
                       "<a href='/contact'>contact us</a> for further assistance."
            self.add_message(_message, 'success')
            return self.redirect_to('login')
        _message = 'Your email / username was not found. Please try another or <a href="/register">create an account</a>.'
        self.add_message(_message, 'error')
        return self.redirect_to('password-reset')


class SendPasswordResetEmailHandler(BaseHandler):
    """
    Hanlder for sending Emails
    Better use with TaskQueue
    """
    def post(self):
        user_address = self.request.get("recipient_email")
        user_token = self.request.get("token")
        user_id = self.request.get("user_id")
        reset_url = self.uri_for('password-reset-check', user_id=user_id, token=user_token, _full=True)
        app_id = app_identity.get_application_id()
        sender_address = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)
        subject = "Password reminder"
        body = """
            Please click below to create a new password:

            %s
            """ % reset_url

        mail.send_mail(sender_address, user_address, subject, body)


class PasswordResetCompleteHandler(BaseHandler):

    def get(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        params = {
            'action': self.request.url,
            'form': self.form
            }
        if verify[0] is None:
            self.add_message('There was an error. Please copy and paste the link from your email or enter your details again below to get a new one.', 'warning')
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
            self.add_message('Password changed successfully', 'success')
            return self.redirect_to('secure')

        else:
            self.add_message('Please correct the form errors.', 'error')
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
        params = {
            'action': self.request.url,
            }
        if verify[0] is None:
            self.add_message('There was an error. Please copy and paste the link from your email.', 'warning')
            self.redirect_to('secure')
        
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


class LoginHandler(BaseHandler):
    """
    Handler for authentication
    """
    def get(self):
        """
              Returns a simple HTML form for login
        """
        if self.user:
            self.redirect_to('secure', id=self.user_id)
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

        if utils.is_email_valid(username):
            user = models.User.get_by_email(username)
            auth_id = user.auth_ids[0]
        else:
            auth_id = "own:%s" % username

        password = self.form.password.data.strip()
        remember_me = True if str(self.request.POST.get('remember_me')) == 'on' else False

        # Password to SHA512
        password = utils.encrypt(password, config.salt)

        # Try to login user with password
        # Raises InvalidAuthIdError if user is not found
        # Raises InvalidPasswordError if provided password
        # doesn't match with specified user
        try:
            self.auth.get_user_by_password(
                auth_id, password, remember=remember_me)
            visitLog = models.VisitLog(
                uastring = self.request.user_agent,
                ip = self.request.remote_addr,
                timestamp = utils.get_date_time()
            )
            visitLog.put()
            self.redirect_to('secure')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            message = "Login invalid, Try again"
            self.add_message(message, 'error')
            return self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self.request.POST)


class ContactHandler(BaseHandler):
    """
    Handler for Contact Form
    """
    def get(self):
        """
              Returns a simple HTML for contact form
        """
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            if user_info.name or user_info.last_name:
                self.form.name.data = user_info.name + " " + user_info.last_name
            if user_info.email:
                self.form.email.data = user_info.email
        params = {
            "action": self.request.url,
            "form": self.form
            }

        return self.render_template('boilerplate_contact.html', **params)

    def post(self):
        """
              validate contact form
        """
        if not self.form.validate():
            return self.get()
        remoteip  = self.request.remote_addr
        user_agent  = self.request.user_agent
        name = self.form.name.data.strip()
        email = self.form.email.data.lower()
        message = self.form.message.data.strip()

        try:
            app_id = app_identity.get_application_id()
            sender_address = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)
            subject = "Contact"
            body = """
            IP Address : %s
            Web Browser  : %s

            Sender : %s <%s>
            %s
            """ % (remoteip, user_agent, name, email, message)

            mail.send_mail(sender_address, config.contact_recipient, subject, body)

            message = 'Message sent successfully.'
            self.add_message(message, 'success')
            return self.redirect_to('contact')

        except (AttributeError, KeyError), e:
            message = 'Error sending the message. Please try again later.'
            self.add_message(message, 'error')
            return self.redirect_to('contact')

    @webapp2.cached_property
    def form(self):
        return forms.ContactForm(self.request.POST)

class RegisterHandler(BaseHandler):
    """
    Handler for Register Users
    """
    def get(self):
        """
              Returns a simple HTML form for create a new user
        """
        if self.user:
            self.redirect_to('secure', id=self.user_id)
        params = {
            "action": self.request.url,
            "form": self.form
            }
        return self.render_template('boilerplate_register.html', **params)

    def post(self):
        """
              Get fields from POST dict
        """
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
        )

        if not user[0]: #user is a tuple
            message = 'Sorry, This user {0:>s} ' \
                      'is already registered.'.format(username)# Error message
            self.add_message(message, 'error')
            return self.redirect_to('register')
        else:
            # User registered successfully, let's try sign in the user and redirect to a secure page.
            try:
                self.auth.get_user_by_password(user[1].auth_ids[0], password)
                message = 'Welcome %s you are now loged in.' % ( str(username) )
                self.add_message(message, 'success')
                return self.redirect_to('secure')

            except (AttributeError, KeyError), e:
                message = 'Unexpected error creating ' \
                          'user {0:>s}.'.format(username)
                self.add_message(message, 'error')
                self.abort(403)

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.RegisterMobileForm(self.request.POST)
        else:
            return forms.RegisterForm(self.request.POST)

class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """
    @user_required
    def get(self):
        """
              Returns a simple HTML form for edit profile
        """
        params = {
            "action": self.request.url,
            "form": self.form
            }
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            self.form.username.data = user_info.username
            self.form.name.data = user_info.name
            self.form.last_name.data = user_info.last_name
            # self.form.email.data = user_info.email
            self.form.country.data = user_info.country

        return self.render_template('boilerplate_edit_profile.html', **params)

    def post(self):
        """
              Get fields from POST dict
        """
        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        # email = self.form.email.data.lower()
        country = self.form.country.data

        new_auth_id='own:%s' % username
        

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            try:
                #checking if new username exists
                message=''
                new_user_info=models.User.get_by_auth_id(new_auth_id)
                if new_user_info==None:
                    user_info.username=username
                    user_info.auth_ids[0]=new_auth_id
                    message+=' Your new username is %s .' % username
                    
                else:
                    if user_info.username == new_user_info.username:
                        message+='Your new username is %s.' % username
                    else:
                        message+='Username: %s is already taken. It is not changed.' % username
                user_info.unique_properties = ['username','email']
                # user_info.email=email
                user_info.name=name
                user_info.last_name=last_name
                user_info.country=country
                user_info.put()
                logging.error(user_info)
                message+=' Your profile has been updated! '
                self.add_message(message,'success')
                self.redirect_to('edit-profile')
            except (AttributeError,KeyError), e:
                message='Unable to update profile!'
                self.add_message(message,'error')
                self.redirect_to('edit-profile')

        except (AttributeError,TypeError),e:
            login_error_message='Sorry you are not logged in!'
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
        """
              Returns a simple HTML form for editing password
        """
        params = {
            "action": self.request.url,
            "form": self.form
            }
        return self.render_template('boilerplate_edit_password.html', **params)

    def post(self):
        """
              Get fields from POST dict
        """
        if not self.form.validate():
            return self.get()
        current_password = self.form.current_password.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
        
            auth_id = "own:%s" % user_info.username
            current_password = utils.encrypt(current_password, config.salt)
            try:
                user=models.User.get_by_auth_password(auth_id, current_password)
                password = utils.encrypt(password, config.salt)
                user.password = security.generate_password_hash(password, length=12)
                user.put()
                
                # send email
                subject = "Boilerplate Account Password Changed"
                app_id = app_identity.get_application_id()
                sender_address = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)
                
                # load email's template
                template_val = {
                    "first_name": user.name,
                    "username": user.username,
                    "email": user.email,
                    "reset_password_url": self.uri_for("password-reset", _full=True)
                }
                email_body_path = "emails/password_changed.txt"
                email_body = self.jinja2.render_template(email_body_path, **template_val)
                mail.send_mail(sender_address, user.email, subject, email_body)
                
                #Login User
                coto = self.auth.get_user_by_password(user.auth_ids[0], password)
                logging.error(coto)
                self.add_message('Password changed successfully', 'success')
                return self.redirect_to('secure')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = "Your Current Password is wrong, please try again"
                self.add_message(message, 'error')
                return self.redirect_to('edit-password')
        except (AttributeError,TypeError), e:
            login_error_message='Sorry you are not logged in!'
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
        """
              Returns a simple HTML form for edit email
        """
        params = {
            "action": self.request.url,
            }
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))

            params.update({
                "email" : user_info.email
            })

        return self.render_template('boilerplate_edit_email.html', **params)

    def post(self):
        """
              Get fields from POST dict
        """
        new_email = self.request.POST.get('new_email').strip()
        password = self.request.POST.get('password').strip()
        
        if new_email == "" or password == "":
            message = 'Sorry, some fields are required.'
            self.add_message(message, 'error')
            return self.redirect_to('edit-email')
        
        if not utils.is_email_valid(new_email):
            message = 'Sorry, the email %s is not valid.' % new_email
            self.add_message(message, 'error')
            return self.redirect_to('edit-email')
        
        try:
            user_info = models.User.get_by_id(long(self.user_id))
            
            auth_id = "own:%s" % user_info.username
            password = utils.encrypt(password, config.salt)
            
            try:
                # authenticate user by its password
                user = models.User.get_by_auth_password(auth_id, password)
                
                # if the user change his/her email address
                if new_email != user.email:
                    subject = "Boilerplate Email Changed Notification"
                    app_id = app_identity.get_application_id()
                    sender_address = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)
                    user_token = models.User.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for("email-changed-check", 
                        user_id = user_info.get_id(),
                        encoded_email = utils.encode(new_email),
                        token = user_token,
                        _full = True)
                    
                    # load email's template
                    template_val = {
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
                    
                    mail.send_mail(sender_address, user.email, subject, old_body)
                    mail.send_mail(sender_address, new_email , subject, new_body)
                    
                    logging.error(user)
                    
                    # display successful message
                    msg = "Please check your new email for confirmation. "
                    msg += "Your email will be updated after confirmation. "
                    self.add_message(msg, 'success')
                    return self.redirect_to('secure')
                    
                else:
                    self.add_message("You didn't change your email", "warning")
                    return self.redirect_to("edit-email")
                
                
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = "Your password is wrong, please try again"
                self.add_message(message, 'error')
                return self.redirect_to('edit-email')
                
        except (AttributeError,TypeError), e:
            login_error_message='Sorry you are not logged in!'
            self.add_message(login_error_message,'error')
            self.redirect_to('login')


class LogoutHandler(BaseHandler):
    """
         Destroy user session and redirect to login
    """
    def get(self):
        if self.user:
            message = "You’ve signed out successfully." # Info message
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
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
            return "Secure zone error: %s." % e
