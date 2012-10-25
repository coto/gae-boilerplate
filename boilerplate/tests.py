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
import webtest
from google.appengine.ext import testbed

from mock import Mock
from mock import patch

import boilerplate
from boilerplate import models
from boilerplate import routes
from boilerplate import routes as boilerplate_routes
from boilerplate import base_config as boilerplate_config
from boilerplate.lib import utils
from boilerplate.lib import captcha
from boilerplate.lib import i18n
from boilerplate.lib import test_helpers

# setting HTTP_HOST in extra_environ parameter for TestApp is not enough for taskqueue stub
os.environ['HTTP_HOST'] = 'localhost'

# globals
network = False

# mock Internet calls
if not network:
    i18n.get_territory_from_ip = Mock(return_value=None)


class AppTest(unittest.TestCase, test_helpers.HandlerHelpers):
    def setUp(self):

        webapp2_config = boilerplate_config.config

        # create a WSGI application.
        self.app = webapp2.WSGIApplication(config=webapp2_config)
        routes.add_routes(self.app)
        boilerplate_routes.add_routes(self.app)
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

        self.headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_4) Version/6.0 Safari/536.25',
                        'Accept-Language' : 'en_US'}

        # fix configuration if this is still a raw boilerplate code - required by test with mails
        if not utils.is_email_valid(self.app.config.get('contact_sender')):
            self.app.config['contact_sender'] = "noreply-testapp@example.com"
        if not utils.is_email_valid(self.app.config.get('contact_recipient')):
            self.app.config['contact_recipient'] = "support-testapp@example.com"

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
        self.submit(form, expect_error=True, error_message='Your username or password is incorrect')
        self.assert_user_not_logged_in()

    def test_login_not_activated(self):
        self.register_testuser()

        form = self.get_form('/', 'form_login_user')
        form['username'] = 'testuser'
        form['password'] = '123456'
        self.submit(form, expect_error=True, error_message='Please check your email to activate it')
        self.assert_user_not_logged_in()
        
    def _login_openid(self, provider, uid, email=None):
        openid_user = Mock()
        openid_user.federated_identity.return_value = uid
        openid_user.email.return_value = email
        with patch('google.appengine.api.users.get_current_user', return_value=openid_user):
            response = self.get('/social_login/{}/complete'.format(provider), status=302)
            response = response.follow(status=200, headers=self.headers) 
        return response

    def test_login_openid_add_association(self):
        response = self._login_openid('google', 'http://www.google.com/accounts/123')
        self.assert_success_message_in_response(response, 'association successfully added.')
        self.assert_user_logged_in()

    def test_login_openid_with_email_add_association(self):
        response = self._login_openid('google', 'http://www.google.com/accounts/123', 'testuser@example.com')
        self.assert_success_message_in_response(response, 'association successfully added.')
        self.assert_user_logged_in()
        user = models.User.query().get()
        self.assertEqual('testuser@example.com', user.email)

    def test_login_openid(self):
        user = self.register_activate_testuser()
        models.SocialUser(user=user.key, provider='google', uid='http://www.google.com/accounts/123').put()
        self._login_openid('google', uid='http://www.google.com/accounts/123')
        self.assert_user_logged_in(user_id=user.get_id())

    def test_login_twitter_no_association(self):
        response = self._test_login_twitter()
        self.assert_warning_message_in_response(response,
                        "This Twitter account is not associated with any local account.")
        self.assert_user_not_logged_in()
 
    def test_login_twitter(self):
        user = self.register_activate_testuser()
        models.SocialUser(user=user.key, provider='twitter', uid='7588892').put()
        self._test_login_twitter()
        self.assert_user_logged_in()
 
    def _test_login_twitter(self):
        oauth_token = 'NPcudxy0yU5T3tBzho7iCotZ3cnetKwcTIRlX0iwRl0'
        oauth_token_secret = 'veNRnAWe6inFuo8o2u8SLLZLjolYDmDP7SzL0YfYI'
        oauth_callback_confirmed = 'true'
        oauth_verifier = 'uw7NjWHT6OJ1MpJOXsHfNxoAhPKpgI8BlYDhxEjIBY'
        user_id = '7588892'
        access_token = '{}-kagSNqWge8gB1WwE3plnFsJHAZVfxWD7Vb57p0b4'.format(user_id)
        oauth_token_secret2 = 'PbKfYqSryyeKDWz4ebtY3o5ogNLG11WJuZBc9fQrQo'
        screen_name = 'testuser'

        class Response:
            def __init__(self, content):
                self.content = content
            def readlines(self):
                return self.content.split('\n')

        urlopen = Mock(side_effect=[Response('oauth_token={}&oauth_token_secret={}&oauth_callback_confirmed=true'.
                                           format(oauth_token, oauth_token_secret, oauth_callback_confirmed)),
                                  Response('oauth_token={}&oauth_token_secret={}&user_id={}&screen_name={}'.
                                           format(access_token, oauth_token_secret2, user_id, screen_name)),
                                  Response('{"id":%s}' % user_id)])
        with patch('urllib2.urlopen', urlopen):
            response = self.get('/social_login/twitter', status=302)
            self.assertTrue(response.headers['Location'].startswith('http://api.twitter.com/oauth/authenticate?'))

            self.assertEquals(urlopen.call_count, 1)
            self.assertTrue(urlopen.call_args_list[0][0][0].
                            startswith('https://api.twitter.com/oauth/request_token?'))

            response = self.get('/social_login/twitter/complete?oauth_token={}&oauth_verifier={}'.
                                format(oauth_token, oauth_verifier), status=302)
            self.assertEquals(urlopen.call_count, 2)
            self.assertTrue(urlopen.call_args_list[1][0][0].
                            startswith('https://api.twitter.com/oauth/access_token?'))
 
            response = response.follow(status=200, headers=self.headers)
            return response
 
    def test_resend_activation_mail(self):
        self.register_testuser()

        # login with valid credentials
        form = self.get_form('/', 'form_login_user')
        form['username'] = 'testuser'
        form['password'] = '123456'
        # account is not activated
        response = self.submit(form, expect_error=True, error_message='Please check your email to activate it')
        self.assert_user_not_logged_in()
        # "lose" activation mail
        self.get_sent_messages(to='testuser@example.com')[0]

        # resend the activation mail
        response2 = response.click(description='click here').follow(status=200, headers=self.headers)
        self.assert_success_message_in_response(response2,
                "The verification email has been resent to testuser@example.com.")

        # click again should fail
        response = response.click(description='click here').follow(status=200, headers=self.headers)
        self.assert_error_message_in_response(response, 'The link is invalid.')

        message = self.get_sent_messages(to='testuser@example.com')[0]
        url = self.get_url_from_message(message, 'activation')
        response = self.get(url, status=302).follow(status=200, headers=self.headers)
        self.assert_success_message_in_response(response,
                message='Congratulations, Your account testuser has been successfully activated.')

    def test_request_with_no_user_agent_header(self):
        self.get('/', headers={'Accept-Language' : 'en_US'})

    def test_request_with_no_accept_language_header(self):
        self.get('/', headers={'User-Agent' : 'Safari'})

    def test_request_with_no_headers(self):
        self.get('/', headers=None)

    def test_edit_profile(self):
        self.get('/settings/profile', status=302) # not for anonymous
        user = self.register_activate_login_testuser()

        form = self.get_form('/settings/profile', 'form_edit_profile')
        self.assertEqual(form['username'].value, 'testuser')
        self.assertEqual(form['name'].value, '')
        self.assertEqual(form['last_name'].value, '')
        self.assertEqual(form['country'].value, '')
        self.submit(form, success_message='your settings have been saved.')

        form['username'] = 'testuser2'
        form['name'] = 'Test'
        form['last_name'] = 'User'
        form['country'] = 'US'
        self.submit(form, success_message='your settings have been saved.')
        self.assertEqual(user.username, 'testuser2')
        self.assertEqual(user.name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.country, 'US')

        self.testapp.reset()
        self.login_user('testuser2', '123456')

    def test_logout(self):
        self.register_activate_login_testuser()
        self.get('/logout/', status=302)
        self.assert_user_not_logged_in()

    def test_edit_email(self):
        user = self.register_activate_login_testuser()

        form = self.get_form('/settings/email', 'form_edit_email', expect_fields=['new_email', 'password'])
        form['new_email'] = 'invalid_email-example.com'
        form['password'] = '123456'
        self.submit(form, expect_error=True, error_message='Invalid email address.')
        form['new_email'] = 'tu@example.com'
        form['password'] = '123'
        self.submit(form, expect_error=True, error_message='Incorrect password!')
        form['password'] = '123456'
        self.submit(form, success_message='Please check your new email for confirmation')

        message_old_address = self.get_sent_messages(to='testuser@example.com', reset_mail_stub=False)[0]
        message_new_address = self.get_sent_messages(to='tu@example.com')[0]
        self.assertEqual(message_old_address.sender, self.app.config.get('contact_sender'))
        self.assertEqual(message_new_address.sender, self.app.config.get('contact_sender'))
        self.assertIn("Recently you've changed the email address", message_old_address.html.payload)
        self.assertIn("You've changed the email address", message_new_address.html.payload)

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
        with patch('boilerplate.lib.captcha.submit', return_value=captcha.RecaptchaResponse(is_valid=False)):
            self.submit(form, expect_error=True, error_message='Wrong image verification code.')
        with patch('boilerplate.lib.captcha.submit', return_value=captcha.RecaptchaResponse(is_valid=True)):
            response1 = self.submit(form, warning_message="you will receive an e-mail from us with instructions for resetting your password.")
            form['email_or_username'] = 'user_does_not_exists'
            response2 = self.submit(form, warning_message="you will receive an e-mail from us with instructions for resetting your password.")
            page1 = response1.body, response1.request.url
            page2 = response2.body.replace('user_does_not_exists', 'testuser'), response2.request.url
            self.assertEqual(page1, page2, "for security reasons application should respond with the same page here")

        message = self.get_sent_messages(to='testuser@example.com')[0]
        self.assertEqual(message.sender, self.app.config.get('contact_sender'))
        self.assertIn('click the link below:', message.html.payload)

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
        self.register_activate_login_testuser()
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
        self.submit(form, success_message='You were successfully registered. Please check your email to activate your account')

        message = self.get_sent_messages(to='reguser@example.com')[0]
        url = self.get_url_from_message(message, 'activation')

        # try to activate account with invalid token
        response = self.get(url+'qwe', status=302).follow(status=200, headers=self.headers)
        self.assert_error_message_in_response(response, 'The link is invalid.')

        response = self.get(url, status=302).follow(status=200, headers=self.headers)
        self.assert_success_message_in_response(response,
                message='Congratulations, Your account reguser has been successfully activated.')

        # activation token has already been used
        response = self.get(url, status=302).follow(status=200, headers=self.headers)
        self.assert_error_message_in_response(response, 'The link is invalid.')

        # activated user should be auto-logged in
        self.assert_user_logged_in()

    def test_contact(self):
        form = self.get_form('/contact/', 'form_contact',
                            expect_fields=['exception', 'name', 'email', 'message'])
        form['name'] = 'Anton'
        form['email'] = 'anton@example.com'
        form['message'] = 'Hi there...'
        self.submit(form)
        message = self.get_sent_messages(to=self.app.config.get('contact_recipient'))[0]
        self.assertEqual(message.sender, self.app.config.get('contact_sender'))
        self.assertIn('Hi there...', message.html.payload)

        self.register_activate_login_testuser()
        form = self.get_form('/contact/', 'form_contact')
        self.assertEqual(form['name'].value, '')
        self.assertEqual(form['email'].value, 'testuser@example.com')
        self.assertEqual(form['message'].value, '')
        form['message'] = 'help'
        self.submit(form, expect_error=True, error_field='name')
        form['name'].value = 'Antonioni'
        self.submit(form, expect_error=False)
        message = self.get_sent_messages(to=self.app.config.get('contact_recipient'))[0]
        self.assertIn('help', message.html.payload)


class ModelTest(unittest.TestCase):
    def setUp(self):

        # activate GAE stubs
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_user_token(self):
        user = models.User(name="tester", email="tester@example.com")
        user.put()
        user2 = models.User(name="tester2", email="tester2@example.com")
        user2.put()

        token = models.User.create_signup_token(user.get_id())
        self.assertTrue(models.User.validate_signup_token(user.get_id(), token))
        self.assertFalse(models.User.validate_resend_token(user.get_id(), token))
        self.assertFalse(models.User.validate_signup_token(user2.get_id(), token))


if __name__ == "__main__":
    unittest.main()
