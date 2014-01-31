'''
Common helper utilities for testing.
'''

import webapp2
import re
from webapp2_extras import auth
from boilerplate import models


class HandlerHelpers():

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

    def submit(self, form, expect_error=False, error_message='', error_field='', success_message='', warning_message=''):
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
            if warning_message:
                self.assert_warning_message_in_response(response, message=warning_message)
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
        # activated user should be auto-logged in
        self.assertTrue(user.activated)
        self.assert_user_logged_in()

    def register_activate_login_testuser(self):
        user = self.register_testuser()
        self.activate_user(user)
        return user

    def register_activate_testuser(self):
        user = self.register_testuser()
        self.activate_user(user)
        self.testapp.reset()
        return user

    def register_testuser(self, **kwargs):
        return self.register_user('testuser', '123456', 'testuser@example.com', **kwargs)

    def register_user(self, username, password, email):
        """Register new user account.

        Optionally activate account and login with username and password."""
        form = self.get_form('/register/', 'form_register')
        form['username'] = username
        form['email'] = email
        form['password'] = password
        form['c_password'] = password
        self.submit(form)

        users = models.User.query(models.User.username == username).fetch(2)
        self.assertEqual(1, len(users), "{} could not register".format(username))
        user = users[0]

        return user

    def get_user_data_from_session(self):
        """Retrieve user info from session."""
        cookies = "; ".join(["{}={}".format(k, v) for k, v in self.testapp.cookies.items()])
        request = webapp2.Request.blank('/', headers=[('Cookie', cookies)])
        request.app = self.app
        a = auth.Auth(request=request)
        return a.get_user_by_session()

    def assert_user_logged_in(self, user_id=None):
        """Check if user is logged in."""
        cookie_name = self.app.config.get('webapp2_extras.auth').get('cookie_name')
        self.assertIn(cookie_name, self.testapp.cookies,
                      'user is not logged in: session cookie not found')
        user = self.get_user_data_from_session()
        if user is None:
            self.fail('user is not logged in')
        if user_id:
            self.assertEqual(user['user_id'], user_id, 'unexpected user is logged in')

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

    def assert_warning_message_in_response(self, response, message=''):
        """Check if response contains one or more warning messages.

        Assume warning messages rendered as <p class="alert-warning"> elements.
        """
        alert = response.pyquery('p.alert-warning')
        self.assertGreater(len(alert), 0, 'no warning message found in response')
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
        m = re.search("http://\S+?(/{}/\S+)".format(pattern), message.html.payload, re.MULTILINE)
        self.assertIsNotNone(m, "{} link not found in mail body".format(pattern))
        return m.group(1)