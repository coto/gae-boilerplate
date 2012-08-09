'''
Run the tests using testrunner.py script in the project root directory.

Usage: testrunner.py SDK_PATH TEST_PATH
Run unit tests for App Engine apps.

SDK_PATH    Path to the SDK installation
TEST_PATH   Path to package containing test modules

Options:
  -h, --help  show this help message and exit

'''
import unittest
import webapp2
import os
import re
import webtest
from google.appengine.ext import testbed
from webapp2_extras import auth
from mock import Mock
from mock import patch

import config
import routes
import web
import models.models as models
from lib import utils
from lib import captcha
from lib import i18n

# setting HTTP_HOST in extra_environ parameter for TestApp is not enough for taskqueue stub
os.environ['HTTP_HOST'] = 'localhost'

# globals
cookie_name = config.webapp2_config['webapp2_extras.auth']['cookie_name']
network = False

# mock Internet calls
if not network:
    i18n.get_territory_from_ip = Mock(return_value=None)


class AppTest(unittest.TestCase):    
    def setUp(self):
        
        # fix configuration if this is still a raw boilerplate code - required by tests with mails
        if not utils.is_email_valid(config.contact_sender):
            config.contact_sender = "noreply-testapp@example.com"
        if not utils.is_email_valid(config.contact_recipient):
            config.contact_recipient = "support-testapp@example.com"

        # create a WSGI application.
        w2config = config.webapp2_config
        # use absolute path for templates
        w2config['webapp2_extras.jinja2']['template_path'] =  os.path.join(os.path.join(os.path.dirname(web.__file__), '..'), 'templates')
        self.app = webapp2.WSGIApplication(config=w2config)
        routes.add_routes(self.app)
        self.testapp = webtest.TestApp(self.app, extra_environ={'REMOTE_ADDR' : '127.0.0.1'})

        # activate GAE stubs
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_urlfetch_stub()
        self.testbed.init_taskqueue_stub()
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
        self.testbed.init_user_stub()
        
        self.headers = {'User-Agent' : 'Safari', 'Accept-Language' : 'en_US'}
                
    def tearDown(self):
        self.testbed.deactivate()
        
    def test_homepage(self):
        response = self.get('/')
        self.assertIn('Congratulations on your Google App Engine Boilerplate powered page.', response)

    def test_csrf_protection(self):
        self.register_activate_testuser()
        self.post('/login/',
                dict(username='testuser', password='password'), status=403)

    def test_login_from_homepage(self):
        self.register_activate_testuser()
        
        form = self.get_form('/', 'form_login_user')
        form['username'] = 'testuser'
        form['password'] = '123456'
        self.submit(form)
        self.assert_user_logged_in()

    def test_login_invalid_password(self):
        self.register_activate_testuser()
 
        form = self.get_form('/', 'form_login_user')
        form['username'] = 'testuser'
        form['password'] = 'wrongpassword'
        self.submit(form, expect_error=True, error_message='Login invalid')
        self.assert_user_not_logged_in()

    def test_login_not_activated(self):
        self.register_testuser()

        form = self.get_form('/', 'form_login_user')
        form['username'] = 'testuser'
        form['password'] = '123456'
        self.submit(form, expect_error=True, error_message='Please check your email to activate your account.')
        self.assert_user_not_logged_in()

    def test_request_with_no_user_agent_header(self):
        self.get('/', headers={'Accept-Language' : 'en_US'})

    def test_request_with_no_accept_language_header(self):
        self.get('/', headers={'User-Agent' : 'Safari'})

    def test_request_with_no_headers(self):
        self.get('/', headers=None)
    
    def test_edit_profile(self):
        self.get('/settings/profile', status=302) # not for anonymous
        user = self.register_testuser(with_login=True)

        form = self.get_form('/settings/profile', 'form_edit_profile')
        self.assertEqual(form['username'].value, 'testuser')
        self.assertEqual(form['name'].value, '')
        self.assertEqual(form['last_name'].value, '')
        self.assertEqual(form['country'].value, '')
        self.submit(form, success_message='Your profile has been updated!')
        
        form['username'] = 'testuser2'
        form['name'] = 'Test'
        form['last_name'] = 'User'
        form['country'] = 'US'
        self.submit(form, success_message='Your profile has been updated!')
        self.assertEqual(user.username, 'testuser2')
        self.assertEqual(user.name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.country, 'US')
        
        self.testapp.reset()
        self.login_user('testuser2', '123456')
        
    def test_logout(self):
        self.register_testuser(with_login=True)
        self.get('/logout/', status=302)
        self.assert_user_not_logged_in()

    def test_edit_email(self):
        user = self.register_testuser(with_login=True)
        
        form = self.get_form('/settings/email', 'form_edit_email', expect_fields=['new_email', 'password'])
        form['new_email'] = 'invalid_email-example.com'
        form['password'] = '123456'
        self.submit(form, expect_error=True, error_message='Invalid email address.')
        form['new_email'] = 'tu@example.com'
        form['password'] = '123'
        self.submit(form, expect_error=True, error_message='Your password is wrong')
        form['password'] = '123456'
        self.submit(form, success_message='Please check your new email for confirmation')

        message_old_address = self.get_sent_messages(to='testuser@example.com', reset_mail_stub=False)[0]
        message_new_address = self.get_sent_messages(to='tu@example.com')[0]
        self.assertEqual(message_old_address.sender, config.contact_sender)
        self.assertEqual(message_new_address.sender, config.contact_sender)
        self.assertIn("Recently you've changed the email address", message_old_address.body.payload)
        self.assertIn("You've changed the email address", message_new_address.body.payload)
        
        self.assertEqual(user.email, 'testuser@example.com')
 
        # click confirmation link
        url = self.get_url_from_message(message_new_address, 'change-email')
        self.get(url, status=302)

        self.assertEqual(user.email, 'tu@example.com')

    def test_password_reset(self):
        self.register_activate_testuser()
 
        form = self.get_form('/password-reset/', 'form_reset_password',
                             expect_fields=['email_or_username', 'recaptcha_challenge_field', 'recaptcha_response_field'])        
        form['email_or_username'] = 'testuser'        
        with patch('lib.captcha.submit', return_value=captcha.RecaptchaResponse(is_valid=False)):
            self.submit(form, expect_error=True, error_message='Wrong image verification code.')
        with patch('lib.captcha.submit', return_value=captcha.RecaptchaResponse(is_valid=True)):
            self.submit(form, success_message="you will receive an e-mail from us with instructions for resetting your password.")

        message = self.get_sent_messages(to='testuser@example.com')[0]
        self.assertEqual(message.sender, config.contact_sender)
        self.assertIn('Please click below to create a new password', message.body.payload)

        # click password reset link and submit new password
        url = self.get_url_from_message(message, 'password-reset')
        self.get(url)
        form = self.get_form(url, 'form_new_password', expect_fields=['password', 'c_password'])
        self.assert_user_not_logged_in()
        form['password'] = form['c_password'] = '456456'
        self.submit(form, success_message='Password changed successfully')
        
        self.testapp.reset()
        self.login_user('testuser', '456456')
        
    def test_edit_password(self):
        self.register_testuser(with_login=True)
        form = self.get_form('/settings/password', 'form_edit_password',
                             expect_fields=['current_password', 'password', 'c_password'])
        form['current_password'] = '123456'
        form['password'] = '789789'
        form['c_password'] = '789'
        self.submit(form, expect_error=True, error_message='Passwords must match.')
        form['c_password'] = '789789'
        self.submit(form)
        
        self.testapp.reset()
        self.login_user('testuser', '789789')

    def test_register(self):
        self._test_register('/register/',
                    expect_fields=['username', 'name', 'last_name', 'email', 'password', 'c_password', 'country'])

    def test_register_from_home_page(self):
        self._test_register('/',
                    expect_fields=['username', 'email', 'country', 'password', 'c_password'])

    def _test_register(self, url, form_id='form_register', expect_fields=None):
        form = self.get_form(url, form_id, expect_fields=expect_fields)
        
        # TODO: check mutliple validation errors on the form
        self.submit(form, expect_error=True, error_message='This field is required.', error_field='username')
        form['username'] = 'Reguser'
        form['email'] = 'reguser@example.com'
        form['password'] = form['c_password'] = '456456'
        self.submit(form, success_message='You are now registered. Please check your email to activate your account')

        message = self.get_sent_messages(to='reguser@example.com')[0]
        url = self.get_url_from_message(message, 'activation')
        response = self.get(url, status=302)
        response = response.follow(status=200, headers=self.headers)
        self.assert_success_message_in_response(response,
                message='Congratulations! Your account (@reguser) has just been activated.')
        # activated user should not be auto-logged in yet
        self.assert_user_not_logged_in()

    def test_contact(self):
        form = self.get_form('/contact/', 'form_contact',
                            expect_fields=['exception', 'name', 'email', 'message'])
        form['name'] = 'Anton'
        form['email'] = 'anton@example.com'
        form['message'] = 'Hi there...'
        self.submit(form)
        message = self.get_sent_messages(to=config.contact_recipient)[0]
        self.assertEqual(message.sender, config.contact_sender)
        self.assertIn('Hi there...', message.body.payload)

        self.register_testuser(with_login=True)
        form = self.get_form('/contact/', 'form_contact')
        self.assertEqual(form['name'].value, '')
        self.assertEqual(form['email'].value, 'testuser@example.com')
        self.assertEqual(form['message'].value, '')
        form['message'] = 'help'
        self.submit(form, expect_error=True, error_field='name')
        form['name'].value = 'Antonioni'
        self.submit(form, expect_error=False)
        message = self.get_sent_messages(to=config.contact_recipient)[0]
        self.assertIn('help', message.body.payload)

    def get(self, *args, **kwargs):
        """Wrap webtest get with nicer defaults"""
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
        if 'status' not in kwargs:
            kwargs['status'] = 200
        return self.testapp.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        """Wrap webtest post with nicer defaults"""
        if 'headers' not in kwargs:
            kwargs['headers'] = self.headers
        return self.testapp.post(*args, **kwargs)

    def get_form(self, url, form_id, expect_fields=None):
        """Load the page and retrieve the form by id"""
        response = self.get(url)
        if response.forms:
            forms_msg = "Found forms: " + ", ".join([f for f in response.forms.keys() if isinstance(f, unicode)])
        else:
            forms_msg = 'No forms found.'
        self.assertIn(form_id, response.forms, "form {} not found on the page {}. {}"
                        .format(form_id, url, forms_msg))
#        print response.pyquery('#' + form_id)
        form = response.forms[form_id]
        if expect_fields:
            form_fields = form.fields.keys()
            for special_field in ('_csrf_token', None):
                try:
                    form_fields.remove(special_field)
                except ValueError:
                    pass
            self.assertListEqual(form_fields, expect_fields)
        return form

    def submit(self, form, expect_error=False, error_message='', error_field='', success_message=''):
        """Submit the form"""
        response = form.submit(headers=self.headers)
        if response.status_int == 200:
            if expect_error: # form validation errors result in response 200
                error_label = response.pyquery('label.error')
                error_label_for = error_label.attr('for')
                if expect_error:
                    if error_message:
                        self.assertIn(error_message, error_label.text())
                    if error_field:
                        self.assertEqual(error_field, error_label_for)
                    return response
                else:
                    self.fail("form failed due to field '{}' with error: {}".format(error_label_for, error_label.text()))
            else: # some forms do not redirect
                pass
        elif response.status_int == 302:
            response = response.follow(status=200, headers=self.headers)
        else:
            self.fail("unexpected form response: {}".format(response.status))

        if expect_error:
            self.assert_error_message_in_response(response, message=error_message)
        else:
            self.assert_no_error_message_in_response(response)
            if success_message:
                self.assert_success_message_in_response(response, message=success_message)
        return response

    def login_user(self, username, password):
        """Login user by username and password."""
        form = self.get_form('/', 'form_login_user')
        form['username'] = username
        form['password'] = password
        self.submit(form)
        self.assert_user_logged_in()

    def activate_user(self, user, use_activation_email=True):
        """Activate user account."""
        self.assertFalse(user.activated, 'user has been already activated')
        if use_activation_email:
            # get mail from the appengine stub
            message = self.get_sent_messages(to=user.email)[0]
            # click activation link
            url = self.get_url_from_message(message, 'activation')
            self.get(url, status=302)
        else:
            user.activated = True
            user.put()
        # activated user should not be auto-logged in yet
        self.assertTrue(user.activated)
        self.assert_user_not_logged_in()

    def register_activate_testuser(self):
        user = self.register_testuser()
        self.activate_user(user)
        return user

    def register_testuser(self, **kwargs):
        return self.register_user('testuser', '123456', 'testuser@example.com', **kwargs)

    def register_user(self, username, password, email, with_login=False):
        """Register new user account.
        
        Optionally activate account and login with username and password."""
        form = self.get_form('/register/', 'form_register')
        form['username'] = username
        form['email'] = email
        form['password'] = password
        form['c_password'] = password
        response = self.submit(form)

        users = models.User.query().fetch(2)
        self.assertEqual(1, len(users), "{} could not register".format(username))
        user = users[0]
        
        if with_login:
            self.activate_user(user)
            self.login_user(username, password)
        else:
            # clear cookies
            self.testapp.reset()
        return user

    def get_user_data_from_session(self):
        """Retrieve user info from session."""
        cookies = "; ".join(["{}={}".format(k, v) for k, v in self.testapp.cookies.items()])
        request = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        request.app = self.app
        a = auth.Auth(request=request)
        return a.get_user_by_session()
       
    def assert_user_logged_in(self):
        """Check if user is logged in."""
        self.assertIn(cookie_name, self.testapp.cookies,
                      'user is not logged in: session cookie not found')
        user = self.get_user_data_from_session()
        if user is None:
            self.fail('user is not logged in')

    def assert_user_not_logged_in(self):
        """Check if user is not logged in."""
        self.assertIsNone(self.get_user_data_from_session(), 'user is logged in unexpectedly')

    def assert_error_message_in_response(self, response, message=''):
        """Check if response contains one or more error messages.
        
        Assume error messages rendered as <p class="alert-error"> elements.
        """
        alert = response.pyquery('p.alert-error')
        self.assertGreater(len(alert), 0, 'no error message found in response')
        if message:
            self.assertIn(message, alert.text())

    def assert_success_message_in_response(self, response, message=''):
        """Check if response contains one or more success messages.
        
        Assume success messages rendered as <p class="alert-success"> elements.
        """
        alert = response.pyquery('p.alert-success')
        self.assertGreater(len(alert), 0, 'no success message found in response')
        if message:
            self.assertIn(message, alert.text())

    def assert_no_error_message_in_response(self, response):
        """Check that response has no error messages."""
        el = response.pyquery('p.alert-error')
        self.assertEqual(len(el), 0, 'error message found in response unexpectedly: {}'.format(el.text()))
        el = response.pyquery('label.error')
        self.assertEqual(len(el), 0, 'error message found in response unexpectedly: {}'.format(el.text()))

    def execute_tasks(self, url=None, queue_name='default', expect_tasks=1):
        """Filter and execute tasks accumulated in the task queue stub."""
        tasks = self.taskqueue_stub.get_filtered_tasks(url=url, queue_names=[queue_name])
        if expect_tasks:
            self.assertEqual(expect_tasks, len(tasks),
                    'expect {} task(s) in queue, found {}: {}'.
                    format(expect_tasks, len(tasks), ", ".join([t.name for t in tasks])))
        for task in tasks:
            self.post(task.url, params=task.payload)
            self.taskqueue_stub.DeleteTask(queue_name, task.name)

    def get_sent_messages(self, to=None, expect_messages=1, reset_mail_stub=True):
        """Fetch sent emails accumulated in the mail stub."""
        # in the single threaded test we have to process the tasks before getting mails
        self.execute_tasks(url='/taskqueue-send-email/', expect_tasks=None)
        messages = self.mail_stub.get_sent_messages(to=to)
        # remove ALL messages from mail stub
        # TODO: remove only fetched messages and get rid of reset_mail_stub parameter
        if reset_mail_stub:
            self.mail_stub._cached_messages=[]
        if expect_messages:
            self.assertEqual(expect_messages, len(messages))
        for message in messages:
            self.assertEqual(to, message.to)
        return messages

    def get_url_from_message(self, message, pattern):
        m = re.search("http://\S+?(/{}/\S+)".format(pattern), message.body.payload, re.MULTILINE)
        self.assertIsNotNone(m, "{} link not found in mail body".format(pattern))
        return m.group(1)

if __name__ == "__main__":
    unittest.main()
