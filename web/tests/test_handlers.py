import unittest
import webapp2

from google.appengine.ext import testbed
import webtest

import config
import routes
import os
import web

import models.models as models
from web import forms

class AppTest(unittest.TestCase):
    def setUp(self):
        # create a WSGI application.
        w2config = config.webapp2_config
        # use absolute path for templates
        w2config['webapp2_extras.jinja2']['template_path'] =  os.path.join(os.path.join(os.path.dirname(web.__file__), '..'), 'templates')
        app = webapp2.WSGIApplication(config=w2config)
        routes.add_routes(app)
        self.testapp = webtest.TestApp(app, extra_environ={'REMOTE_ADDR' : '127.0.0.1'})

        # activate GAE stubs
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_urlfetch_stub()

        # some shortcuts
        self.cookie_name=config.webapp2_config['webapp2_extras.auth']['cookie_name']
        self.headers = {'User-Agent' : 'Safari', 'Accept-Language' : 'en_US'}
        
        # register test account
        self.testapp.post('/register/',
                        forms.RegisterForm(username='testuser', password='123456',
                            c_password='123456', email='testuser@example.com', country='').data,
                        headers=self.headers)
        
        # is test account created?
        users = models.User.query().fetch(2)
        self.assertEqual(1, len(users), 'testuser could not register')
        self.user = users[0]

        # clear cookies
        self.testapp.reset()

    def tearDown(self):
        self.testbed.deactivate()
        
    def test_loginFromHomePage(self):
        response = self.testapp.get('/', status=200, headers=self.headers)
        self.assertIn('Congratulations on your Google App Engine Boilerplate powered page.', response)
        
        form = response.forms['form_login_user']
        form['username'] = 'testuser'
        form['password'] = '123456'
        response = form.submit()       
        self.assertUserLoggedIn(response)

    def test_loginSuccess(self):
        response = self.testapp.post('/login/',
                        forms.LoginForm(username='testuser', password='123456').data,
                        status=302, headers=self.headers)
        self.assertUserLoggedIn(response)

    def test_loginInvalid(self):
        response = self.testapp.post('/login/',
                        forms.LoginForm(username='testuser', password='wrongpassword').data,
                        status=302, headers=self.headers)
        self.assertNotIn(self.cookie_name, response.cookies_set)

        response = response.follow(status=200, headers=self.headers)
        self.assertTextInErrorMessage('Login invalid', response)

    def assertUserLoggedIn(self, response):
        self.assertIn(self.cookie_name, response.cookies_set)

    def assertTextInErrorMessage(self, text, response):
        alert = response.pyquery('p.alert-error')
        self.assertGreater(len(alert), 0, 'no error message found in response')
        self.assertIn(text, alert.text())

    def test_requestHeadersNoUserAgent(self):
        self.testapp.get('/', status=200, headers={'Accept-Language' : 'en_US'})

    def test_requestHeadersNoAcceptLanguage(self):
        self.testapp.get('/', status=200, headers={'User-Agent' : 'Safari'})

    def test_requestHeadersNone(self):
        self.testapp.get('/', status=200)


if __name__ == "__main__":
    unittest.main()
