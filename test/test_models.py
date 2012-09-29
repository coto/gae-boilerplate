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
from google.appengine.ext import testbed
from boilerplate import models

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
