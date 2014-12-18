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

from bp_includes import models
from bp_includes import routes as routes_boilerplate
from bp_content.themes.default import routes as routes_theme
from bp_includes import config as config_boilerplate
from bp_content.themes.default import config as config_theme
from bp_includes.lib import utils
from bp_includes.lib import i18n
from bp_includes.lib import test_helpers
from bp_includes.lib import captcha, utils
# setting HTTP_HOST in extra_environ parameter for TestApp is not enough for taskqueue stub
os.environ['HTTP_HOST'] = 'localhost'

# globals
network = False

# mock Internet calls
if not network:
    i18n.get_country_code = Mock(return_value=None)

    # Mock captcha to pass for unit tests
    dummy_response = Mock()
    dummy_response.is_valid = True
    captcha.submit = Mock(return_value=dummy_response)


class AppTest(unittest.TestCase, test_helpers.HandlerHelpers):
    def setUp(self):

        webapp2_config = config_boilerplate.config
        webapp2_config.update(config_theme.config)
        # create a WSGI application.
        self.app = webapp2.WSGIApplication(config=webapp2_config)
        routes_boilerplate.add_routes(self.app)
        routes_theme.add_routes(self.app)
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

    def test_config_environment(self):
        self.assertEquals(self.app.config.get('environment'), 'testing')

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
