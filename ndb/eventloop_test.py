"""Tests for eventloop.py."""

import logging
import os
import time
import unittest

from .google_imports import apiproxy_stub_map
from .google_imports import datastore_rpc

from . import eventloop
from . import test_utils

class EventLoopTests(test_utils.NDBTest):

  def setUp(self):
    super(EventLoopTests, self).setUp()
    if eventloop._EVENT_LOOP_KEY in os.environ:
      del os.environ[eventloop._EVENT_LOOP_KEY]
    self.ev = eventloop.get_event_loop()

  the_module = eventloop

  def testQueueTasklet(self):
    def f(unused_number, unused_string, unused_a, unused_b): return 1
    def g(unused_number, unused_string): return 2
    def h(unused_c, unused_d): return 3
    t_before = time.time()
    eventloop.queue_call(1, f, 42, 'hello', unused_a=1, unused_b=2)
    eventloop.queue_call(3, h, unused_c=3, unused_d=4)
    eventloop.queue_call(2, g, 100, 'abc')
    t_after = time.time()
    self.assertEqual(len(self.ev.queue), 3)
    [(t1, f1, a1, k1), (t2, f2, a2, k2), (t3, f3, a3, k3)] = self.ev.queue
    self.assertTrue(t1 < t2)
    self.assertTrue(t2 < t3)
    self.assertTrue(abs(t1 - (t_before + 1)) <= t_after - t_before)
    self.assertTrue(abs(t2 - (t_before + 2)) <= t_after - t_before)
    self.assertTrue(abs(t3 - (t_before + 3)) <= t_after - t_before)
    self.assertEqual(f1, f)
    self.assertEqual(f2, g)
    self.assertEqual(f3, h)
    self.assertEqual(a1, (42, 'hello'))
    self.assertEqual(a2, (100, 'abc'))
    self.assertEqual(a3, ())
    self.assertEqual(k1, {'unused_a': 1, 'unused_b': 2})
    self.assertEqual(k2, {})
    self.assertEqual(k3, {'unused_c': 3, 'unused_d': 4})
    # Delete queued events (they would fail or take a long time).
    ev = eventloop.get_event_loop()
    ev.queue = []
    ev.rpcs = {}

  def testFifoOrderForEventsWithDelayNone(self):
    order = []
    def foo(arg): order.append(arg)

    eventloop.queue_call(None, foo, 2)
    eventloop.queue_call(None, foo, 1)
    eventloop.queue_call(0, foo, 0)

    self.assertEqual(len(self.ev.current), 2)
    self.assertEqual(len(self.ev.queue), 1)
    [(_f1, a1, _k1), (_f2, a2, _k2)] = self.ev.current
    self.assertEqual(a1, (2,))  # first event should have arg = 2
    self.assertEqual(a2, (1,))  # second event should have arg = 1
    (_t, _f, a, _k) = self.ev.queue[0]
    self.assertEqual(a, (0,))  # third event should have arg = 0

    eventloop.run()
    # test that events are executed in FIFO order, not sort order
    self.assertEqual(order, [2, 1, 0])

  def testRun(self):
    record = []
    def foo(arg):
      record.append(arg)
    eventloop.queue_call(0.2, foo, 42)
    eventloop.queue_call(0.1, foo, arg='hello')
    eventloop.run()
    self.assertEqual(record, ['hello', 42])

  def testRunWithRpcs(self):
    record = []
    def foo(arg):
      record.append(arg)
    eventloop.queue_call(0.1, foo, 42)
    config = datastore_rpc.Configuration(on_completion=foo)
    rpc = self.conn.async_get(config, [])
    if not isinstance(rpc, apiproxy_stub_map.UserRPC):
      self.assertEqual(len(rpc.rpcs), 1)
      rpc = rpc.rpcs[0]
    eventloop.queue_rpc(rpc)
    eventloop.run()
    self.assertEqual(record, [rpc, 42])
    self.assertEqual(rpc.state, 2)  # TODO: Use apiproxy_rpc.RPC.FINISHING.

  def testIdle(self):
    counters = [0, 0, 0]
    def idler1():
      logging.info('idler1 running')
      counters[0] += 1
      return False
    def idler2(a, b=None):
      logging.info('idler2 running: a=%s, b=%s', a, b)
      counters[1] += 1
      return False
    def idler3(k=None):
      logging.info('idler3 running: k=%s', k)
      counters[2] += 1
      return None
    self.ev.add_idle(idler1)
    self.ev.add_idle(idler2, 10, 20)
    eventloop.add_idle(idler3, k=42)
    self.ev.run()
    self.assertEqual(counters, [1, 1, 1])
    self.ev.run()
    self.assertEqual(counters, [2, 2, 1])

  def testMultiRpcReadiness(self):
    from . import key
    k1 = key.Key('Foo', 1)
    k2 = key.Key('Foo', 2)
    r1 = self.conn.async_get(None, [k1])
    r2 = self.conn.async_get(None, [k2])
    rpc = datastore_rpc.MultiRpc([r1, r2])
    r1.wait()
    r2.wait()
    calls = []
    def callback():
      calls.append(1)
    eventloop.queue_rpc(rpc, callback)
    eventloop.run()
    self.assertEqual(calls, [1])

  def testCleanUpStaleEvents(self):
    # See issue 127.  http://goo.gl/2p5Pn
    from . import model
    class M(model.Model): pass
    M().put()
    M().put()
    M().put()
    # The fetch_page() call leaves an unnecessary but unavoidable RPC
    # around that is never waited for.  This was causing problems when
    # it was being garbage-collected in get_event_loop(), especially
    # with Python 2.5, where GeneratorExit derived from Exception.
    M.query().fetch_page(2)
    ev = eventloop.get_event_loop()
    self.assertEqual(len(ev.rpcs), 1)
    del os.environ[eventloop._EVENT_LOOP_KEY]
    ev = eventloop.get_event_loop()  # A new event loop.
    self.assertEqual(len(ev.rpcs), 0)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
