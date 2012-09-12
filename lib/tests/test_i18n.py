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
from google.appengine.ext import ndb
from webapp2_extras import auth
from mock import Mock
from mock import patch

from lib import i18n
import config

class I18nTest(unittest.TestCase):    
    def setUp(self):
        
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
                
    def tearDown(self):
        self.testbed.deactivate()
        
    def testDisableI18n(self):
        config.locales = []
        locale = i18n.set_locale(None)
        self.assertEqual(locale, None)
        config.locales = None 
        locale = i18n.set_locale(None)
        self.assertEqual(locale, None)
        

        
if __name__ == "__main__":
    unittest.main()