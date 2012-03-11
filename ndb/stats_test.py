"""Tests for stats.py."""

import datetime
import os
import unittest

from .google_imports import datastore

from . import stats
from . import test_utils


class StatsTests(test_utils.NDBTest):

  def setUp(self):
    """Setup test infrastructure."""
    super(StatsTests, self).setUp()
    self.PopulateStatEntities()

  the_module = stats

  def PopulateStatEntities(self):
    """Insert stat entities into the datastore."""
    # GlobalStat
    self.CreateStatEntity(stats.GlobalStat.STORED_KIND_NAME,
        has_entity_bytes=True,
        has_builtin_index_stats=True,
        has_composite_index_stats=True)

    # NamespaceStat
    self.CreateStatEntity(stats.NamespaceStat.STORED_KIND_NAME,
        subject_namespace='name-space',
        has_entity_bytes=True,
        has_builtin_index_stats=True,
        has_composite_index_stats=True)

    # KindStat
    self.CreateStatEntity(stats.KindStat.STORED_KIND_NAME, 'foo',
        has_entity_bytes=True,
        has_builtin_index_stats=True,
        has_composite_index_stats=True)
    self.CreateStatEntity(stats.KindStat.STORED_KIND_NAME, 'foo2',
        has_entity_bytes=True,
        has_builtin_index_stats=True,
        has_composite_index_stats=True)

    # KindRootEntityStat
    self.CreateStatEntity(stats.KindRootEntityStat.STORED_KIND_NAME, 'foo3',
                          has_entity_bytes=True)
    self.CreateStatEntity(stats.KindRootEntityStat.STORED_KIND_NAME, 'foo4',
                          has_entity_bytes=True)

    # KindNonRootEntityStat
    self.CreateStatEntity(stats.KindNonRootEntityStat.STORED_KIND_NAME, 'foo5',
                          has_entity_bytes=True)
    self.CreateStatEntity(stats.KindNonRootEntityStat.STORED_KIND_NAME, 'foo6',
                          has_entity_bytes=True)

    # PropertyTypeStat
    self.CreateStatEntity(stats.PropertyTypeStat.STORED_KIND_NAME,
        property_type='pt1',
        has_entity_bytes=True,
        has_builtin_index_stats=True)
    self.CreateStatEntity(stats.PropertyTypeStat.STORED_KIND_NAME,
        property_type='pt2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)

    # KindPropertyTypeStat
    self.CreateStatEntity(stats.KindPropertyTypeStat.STORED_KIND_NAME,
        kind_name='foo1',
        property_type='pt1',
        has_entity_bytes=True,
        has_builtin_index_stats=True)
    self.CreateStatEntity(stats.KindPropertyTypeStat.STORED_KIND_NAME,
        kind_name='foo1',
        property_type='pt2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)
    self.CreateStatEntity(stats.KindPropertyTypeStat.STORED_KIND_NAME,
        kind_name='foo2',
        property_type='pt2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)

    # KindPropertyNameStat
    self.CreateStatEntity(stats.KindPropertyNameStat.STORED_KIND_NAME,
        kind_name='foo11',
        property_name='pn1',
        has_entity_bytes=True,
        has_builtin_index_stats=True)
    self.CreateStatEntity(stats.KindPropertyNameStat.STORED_KIND_NAME,
        kind_name='foo11',
        property_name='pn2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)
    self.CreateStatEntity(stats.KindPropertyNameStat.STORED_KIND_NAME,
        kind_name='foo21',
        property_name='pn2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)

    # KindPropertyNamePropertyTypeStat
    self.CreateStatEntity(
        stats.KindPropertyNamePropertyTypeStat.STORED_KIND_NAME,
        kind_name='foo12',
        property_type='pt1',
        property_name='pn1',
        has_entity_bytes=True,
        has_builtin_index_stats=True)

    self.CreateStatEntity(
        stats.KindPropertyNamePropertyTypeStat.STORED_KIND_NAME,
        kind_name='foo12',
        property_type='pt2',
        property_name='pn2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)

    self.CreateStatEntity(
        stats.KindPropertyNamePropertyTypeStat.STORED_KIND_NAME,
        kind_name='foo22',
        property_type='pt2',
        property_name='pn2',
        has_entity_bytes=True,
        has_builtin_index_stats=True)

    # KindCompositeIndexStat
    self.CreateStatEntity(
        stats.KindCompositeIndexStat.STORED_KIND_NAME,
        kind_name='foo12',
        composite_index_id=1)
    self.CreateStatEntity(
        stats.KindCompositeIndexStat.STORED_KIND_NAME,
        kind_name='foo12',
        composite_index_id=2)
    self.CreateStatEntity(
        stats.KindCompositeIndexStat.STORED_KIND_NAME,
        kind_name='foo22',
        composite_index_id=3)

  def CreateStatEntity(self,
                       kind,
                       kind_name=None,
                       property_type=None,
                       property_name=None,
                       subject_namespace=None,
                       composite_index_id=None,
                       has_entity_bytes=None,
                       has_builtin_index_stats=None,
                       has_composite_index_stats=None):
    """Create a single Statistic datastore entity.

    Args:
      kind: The name of the kind to store.
      kind_name: The value of the 'kind_name' property to set on the entity.
      property_type: The value of the 'property_type' property to set on the
        entity.
      property_name: The value of the 'property_name' property to set on the
        entity.
      subject_namespace: The namespace for NamespaceStat entities.
      composite_index_id: The index id of composite index.
      has_entity_bytes: The stat has the entity_bytes property.
      has_builtin_index_stats: The stat entity has builtin_index_bytes and
        builtin_index_count.
      has_composite_index_stats: The stat entity has composite_index_bytes and
        composite_index_count.
    """
    stat = datastore.Entity(kind)
    stat['bytes'] = 4
    stat['count'] = 2
    stat['timestamp'] = datetime.datetime.utcfromtimestamp(40)
    if has_entity_bytes:
      stat['entity_bytes'] = 2
    if has_builtin_index_stats:
      stat['builtin_index_count'] = 3
      stat['builtin_index_bytes'] = 1
    if has_composite_index_stats:
      stat['composite_index_count'] = 2
      stat['composite_index_bytes'] = 1
    if kind_name is not None:
      stat['kind_name'] = kind_name
    if property_type is not None:
      stat['property_type'] = property_type
    if property_name is not None:
      stat['property_name'] = property_name
    if subject_namespace is not None:
      stat['subject_namespace'] = subject_namespace
    if composite_index_id is not None:
      stat['index_id'] = composite_index_id
    datastore.Put(stat)

  def testGlobalStat(self):
    """Test fetching the global stat singleton."""
    res = stats.GlobalStat.query().fetch()
    self.assertEquals(1, len(res))
    self.assertEquals(4, res[0].bytes)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)
    self.assertEquals(2, res[0].composite_index_count)
    self.assertEquals(1, res[0].composite_index_bytes)

  def testNamespaceStat(self):
    """Test fetching the global stat singleton."""
    res = stats.NamespaceStat.query().fetch()
    self.assertEquals(1, len(res))
    self.assertEquals(4, res[0].bytes)
    self.assertEquals('name-space', res[0].subject_namespace)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)
    self.assertEquals(2, res[0].composite_index_count)
    self.assertEquals(1, res[0].composite_index_bytes)

  def testKindStat(self):
    """Test fetching the Kind stats."""
    res = stats.KindStat.query().fetch()
    self.assertEquals(2, len(res))
    self.assertEquals('foo', res[0].kind_name)
    self.assertEquals('foo2', res[1].kind_name)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)
    self.assertEquals(2, res[0].composite_index_count)
    self.assertEquals(1, res[0].composite_index_bytes)

  def testKindRootEntityStat(self):
    """Test fetching the Kind root entity stats."""
    res = stats.KindRootEntityStat.query().fetch()
    self.assertEquals(2, len(res))
    self.assertEquals('foo3', res[0].kind_name)
    self.assertEquals('foo4', res[1].kind_name)
    self.assertEquals(2, res[0].entity_bytes)

  def testKindNonRootEntityStat(self):
    """Test fetching the Kind non-root entity stats."""
    res = stats.KindNonRootEntityStat.query().fetch()
    self.assertEquals(2, len(res))
    self.assertEquals('foo5', res[0].kind_name)
    self.assertEquals('foo6', res[1].kind_name)
    self.assertEquals(2, res[0].entity_bytes)

  def testPropertyTypeStat(self):
    """Test fetching the property type stats."""
    res = stats.PropertyTypeStat.query().fetch()
    self.assertEquals(2, len(res))
    self.assertEquals('pt1', res[0].property_type)
    self.assertEquals('pt2', res[1].property_type)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)

  def testKindPropertyTypeStat(self):
    """Test fetching the (kind, property type) stats."""
    res = stats.KindPropertyTypeStat.query().fetch()
    self.assertEquals(3, len(res))
    self.assertEquals('foo1', res[0].kind_name)
    self.assertEquals('pt1', res[0].property_type)
    self.assertEquals('foo1', res[1].kind_name)
    self.assertEquals('pt2', res[1].property_type)
    self.assertEquals('foo2', res[2].kind_name)
    self.assertEquals('pt2', res[2].property_type)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)

    query = stats.KindPropertyTypeStat.query(
      stats.KindPropertyTypeStat.kind_name == 'foo2')
    res = query.fetch()
    self.assertEquals(1, len(res))
    self.assertEquals('foo2', res[0].kind_name)

  def testKindPropertyNameStat(self):
    """Test fetching the (kind, property name) type stats."""
    res = stats.KindPropertyNameStat.query().fetch()
    self.assertEquals(3, len(res))
    self.assertEquals('foo11', res[0].kind_name)
    self.assertEquals('pn1', res[0].property_name)
    self.assertEquals('foo11', res[1].kind_name)
    self.assertEquals('pn2', res[1].property_name)
    self.assertEquals('foo21', res[2].kind_name)
    self.assertEquals('pn2', res[2].property_name)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)

    query = stats.KindPropertyNameStat.query(
      stats.KindPropertyNameStat.kind_name == 'foo21')
    res = query.fetch()
    self.assertEquals(1, len(res))
    self.assertEquals('foo21', res[0].kind_name)

  def testKindPropertyNamePropertyTypeStat(self):
    """Test fetching the (kind, property name, property type) stats."""
    res = stats.KindPropertyNamePropertyTypeStat.query().fetch()
    self.assertEquals(3, len(res))
    self.assertEquals('foo12', res[0].kind_name)
    self.assertEquals('pn1', res[0].property_name)
    self.assertEquals('pt1', res[0].property_type)
    self.assertEquals('foo12', res[1].kind_name)
    self.assertEquals('pn2', res[1].property_name)
    self.assertEquals('pt2', res[1].property_type)
    self.assertEquals('foo22', res[2].kind_name)
    self.assertEquals('pn2', res[2].property_name)
    self.assertEquals('pt2', res[2].property_type)
    self.assertEquals(2, res[0].entity_bytes)
    self.assertEquals(3, res[0].builtin_index_count)
    self.assertEquals(1, res[0].builtin_index_bytes)

    query = stats.KindPropertyNamePropertyTypeStat.query(
      stats.KindPropertyNamePropertyTypeStat.kind_name == 'foo22')
    res = query.fetch()
    self.assertEquals(1, len(res))
    self.assertEquals('foo22', res[0].kind_name)

  def testKindCompositeIndex(self):
    """Test fetching the (kind, composite index id) stats."""
    res = stats.KindCompositeIndexStat.query().fetch()
    self.assertEquals(3, len(res))
    self.assertEquals('foo12', res[0].kind_name)
    self.assertEquals(1, res[0].index_id)
    self.assertEquals('foo12', res[1].kind_name)
    self.assertEquals(2, res[1].index_id)
    self.assertEquals('foo22', res[2].kind_name)
    self.assertEquals(3, res[2].index_id)
    self.assertEquals(4, res[0].bytes)
    self.assertEquals(2, res[0].count)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
