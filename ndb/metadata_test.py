"""Tests for metadata.py."""

import unittest

from .google_imports import namespace_manager

from . import metadata
from . import model
from . import test_utils


class MetadataTests(test_utils.NDBTest):

  def setUp(self):
    super(MetadataTests, self).setUp()
    class Foo(model.Model):
      name = model.StringProperty()
      age = model.IntegerProperty()
    self.Foo = Foo
    class Bar(model.Model):
      name = model.StringProperty()
      rate = model.IntegerProperty()
    self.Bar = Bar
    class Ext(model.Expando):
      pass
    self.Ext = Ext
    namespace_manager.set_namespace('')  # Always start in default ns.

  the_module = metadata

  def testGetNamespaces(self):
    self.assertEqual([], metadata.get_namespaces())
    self.Foo().put()
    self.assertEqual([''], metadata.get_namespaces())
    self.assertEqual([], metadata.get_namespaces(None, ''))
    for ns in 'x', 'xyzzy', 'y', 'z':
      namespace_manager.set_namespace(ns)
      self.Foo().put()
    self.assertEqual(['', 'x', 'xyzzy', 'y', 'z'], metadata.get_namespaces())
    self.assertEqual(['x', 'xyzzy'], metadata.get_namespaces('x', 'y'))

  def testGetKinds(self):
    self.assertEqual([], metadata.get_kinds())
    self.Foo().put()
    self.Bar().put()
    self.Ext().put()
    self.assertEqual(['Bar', 'Ext', 'Foo'], metadata.get_kinds())
    self.assertEqual(['Bar', 'Ext'], metadata.get_kinds('A', 'F'))
    self.assertEqual([], metadata.get_kinds(None, ''))
    namespace_manager.set_namespace('x')
    self.assertEqual([], metadata.get_kinds())
    self.Foo().put()
    self.assertEqual(['Foo'], metadata.get_kinds())

  def testGetPropertiesOfKind(self):
    self.Foo().put()
    self.assertEqual(['age', 'name'], metadata.get_properties_of_kind('Foo'))
    self.assertEqual(['age'], metadata.get_properties_of_kind('Foo', 'a', 'h'))
    self.assertEqual([], metadata.get_properties_of_kind('Foo', None, ''))
    e = self.Ext()
    e.foo = 1
    e.bar = 2
    e.put()
    self.assertEqual(['bar', 'foo'], metadata.get_properties_of_kind('Ext'))
    namespace_manager.set_namespace('x')
    e = self.Ext()
    e.one = 1
    e.two = 2
    e.put()
    self.assertEqual(['one', 'two'], metadata.get_properties_of_kind('Ext'))

  def testGetRepresentationsOfKind(self):
    e = self.Ext()
    e.foo = 1
    e.bar = 'a'
    e.put()
    self.assertEqual({'foo': ['INT64'], 'bar': ['STRING']},
                     metadata.get_representations_of_kind('Ext'))
    self.assertEqual({'bar': ['STRING']},
                     metadata.get_representations_of_kind('Ext', 'a', 'e'))
    self.assertEqual({},
                     metadata.get_representations_of_kind('Ext', None, ''))
    f = self.Ext()
    f.foo = 'x'
    f.bar = 2
    f.put()
    self.assertEqual({'foo': ['INT64', 'STRING'],
                      'bar': ['INT64', 'STRING']},
                     metadata.get_representations_of_kind('Ext'))

  def testDirectPropertyQueries(self):
    e = self.Ext()
    e.foo = 1
    e.bar = 'a'
    e.put()
    f = self.Foo(name='a', age=42)
    f.put()
    q = metadata.Property.query()
    res = q.fetch()
    self.assertEqual([('Ext', 'bar'), ('Ext', 'foo'),
                      ('Foo', 'age'), ('Foo', 'name')],
                     [(p.kind_name, p.property_name) for p in res])


def main():
  unittest.main()


if __name__ == '__main__':
  main()
