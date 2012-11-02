import unittest
from google.appengine.ext import testbed
from google.appengine.ext import ndb


class CursorTests(unittest.TestCase):
    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def test_paging(self):
        class Bar(ndb.Model):
            value = ndb.IntegerProperty()

        for i in range(18):
            Bar(value=i+1).put()

        q = Bar.query()
        bars1, _, _ = q.order(Bar.key).fetch_page(3)
        next_cursor = None
        for i in (1,2,3,4,5,6):
            bars, next_cursor, more = q.order(Bar.key).fetch_page(3, start_cursor=next_cursor)
#            print bars, next_cursor, more
            self.assertTrue(more if i != 6 else not more)
            self.assertIsNotNone(next_cursor)
            
        bars2 = bars
        
        rev_cursor = next_cursor.reversed()
        for i in (1,2,3,4,5,6):
            barz, rev_cursor, more2 = q.order(-Bar.key).fetch_page(3, start_cursor=rev_cursor)
#            print barz
         
        self.assertEqual(bars1, list(reversed(barz)))
        self.assertFalse(more2)
#        self.assertEqual(bars, bary)

        rev_cursor = rev_cursor.reversed()
        for i in (1,2,3,4,5,6):
            bars, rev_cursor, more2 = q.order(Bar.key).fetch_page(3, start_cursor=rev_cursor)
#            print bars

        self.assertEqual(bars2, bars)
 