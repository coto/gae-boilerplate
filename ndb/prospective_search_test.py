"""Tests for prospective_search.py."""

import base64
import os
import unittest

from .google_imports import apiproxy_stub_map
from .google_test_imports import prospective_search_stub


from . import prospective_search
from . import model
from . import test_utils


class ProspectiveSearchTests(test_utils.NDBTest):

  def setUp(self):
    super(ProspectiveSearchTests, self).setUp()
    tq_stub = self.testbed.get_stub('taskqueue')
    dummy_fn = os.path.devnull
    ps_stub = prospective_search_stub.ProspectiveSearchStub(dummy_fn, tq_stub)
    self.testbed._register_stub('matcher', ps_stub)

  the_module = prospective_search

  def testSubscribe(self):
    class Foo(model.Model):
      name = model.TextProperty()
      rank = model.IntegerProperty()
      tags = model.StringProperty(repeated=True)
      flag = model.BooleanProperty()
      rand = model.FloatProperty()
      nope = model.KeyProperty()
    prospective_search.subscribe(Foo, 'query', 'sub_id')
    self.assertEqual(prospective_search._model_to_entity_schema(Foo),
                     {str: ['name', 'tags'],
                      int: ['rank'],
                      bool: ['flag'],
                      float: ['rand'],
                      })

  def testUnsubscribe(self):
    class Foo(model.Model):
      pass
    prospective_search.unsubscribe(Foo, 'sub_id')

  def testGetSubscription(self):
    class Foo(model.Model):
      pass
    self.assertRaises(prospective_search.SubscriptionDoesNotExist,
                      prospective_search.get_subscription, Foo, 'sub_id')
    prospective_search.subscribe(Foo, 'query', 'sub_id')
    sub = prospective_search.get_subscription(Foo, 'sub_id')
    sub_id, query, expiration, state, error_message = sub
    self.assertEqual(sub_id, 'sub_id')
    self.assertEqual(query, 'query')
    self.assertTrue(isinstance(expiration, (int, long, float)))
    self.assertEqual(state, 0)
    self.assertEqual(error_message, '')

  def testListSubscriptions(self):
    class Foo(model.Model):
      pass
    prospective_search.subscribe(Foo, 'query', 'sub_id', topic='bar')
    subs = prospective_search.list_subscriptions(Foo)
    self.assertEqual(subs, [])
    subs = prospective_search.list_subscriptions(Foo, topic='bar')
    self.assertEqual(len(subs), 1)
    sub = subs[0]
    sub_id, query, expiration, state, error_message = sub
    self.assertEqual(sub_id, 'sub_id')
    self.assertEqual(query, 'query')
    self.assertTrue(isinstance(expiration, (int, long, float)))
    self.assertEqual(state, 0)
    self.assertEqual(error_message, '')

  def testListTopics(self):
    class Foo(model.Model):
      pass
    prospective_search.subscribe(Foo, 'query', 'sub_id')
    topics = prospective_search.list_topics()
    self.assertEqual(topics, ['Foo'])

  def testMatch(self):
    class Foo(model.Model):
      name = model.StringProperty()
    prospective_search.subscribe(Foo, 'query', 'sub_id')
    ent = Foo(name='fred')
    prospective_search.match(ent)

  def testGetDocument(self):
    class Foo(model.Model):
      name = model.StringProperty()
    ent = Foo(name='fred')
    request = {'python_document_class': prospective_search._doc_class.ENTITY,
               'document': base64.urlsafe_b64encode(ent._to_pb().Encode())}
    ent2 = prospective_search.get_document(request)
    self.assertEqual(ent2, ent)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
