"""Tests for tasklets.py."""

import os
import random
import re
import sys
import time
import unittest

from . import context
from . import eventloop
from . import model
from . import test_utils
from . import tasklets
from . import utils


class TaskletTests(test_utils.NDBTest):

  def setUp(self):
    super(TaskletTests, self).setUp()
    if eventloop._EVENT_LOOP_KEY in os.environ:
      del os.environ[eventloop._EVENT_LOOP_KEY]
    if tasklets._CONTEXT_KEY in os.environ:
      del os.environ[tasklets._CONTEXT_KEY]
    self.ev = eventloop.get_event_loop()
    self.log = []

  the_module = tasklets

  def universal_callback(self, *args):
    self.log.append(args)

  def testAddFlowException(self):
    try:
      self.assertRaises(TypeError, tasklets.add_flow_exception, 'abc')
      self.assertRaises(TypeError, tasklets.add_flow_exception, str)
      tasklets.add_flow_exception(ZeroDivisionError)
      self.assertTrue(ZeroDivisionError in tasklets._flow_exceptions)
      @tasklets.tasklet
      def foo():
        1/0
        yield
      self.assertRaises(ZeroDivisionError, foo().get_result)
    finally:
      tasklets._init_flow_exceptions()

  def testFuture_Constructor(self):
    f = tasklets.Future()
    self.assertEqual(f._result, None)
    self.assertEqual(f._exception, None)
    self.assertEqual(f._callbacks, [])

  def testFuture_Repr(self):
    f = tasklets.Future()
    prefix = (r'<Future [\da-f]+ created by'
              r'( testFuture_Repr\(tasklets_test.py:\d+\)|\?); ')
    self.assertTrue(re.match(prefix + r'pending>$', repr(f)), repr(f))
    f.set_result('abc')
    self.assertTrue(re.match(prefix + r'result \'abc\'>$', repr(f)), repr(f))
    f = tasklets.Future()
    f.set_exception(RuntimeError('abc'))
    self.assertTrue(re.match(prefix + r'exception RuntimeError: abc>$',
                             repr(f)),
                    repr(f))

  def testFuture_Repr_TaskletWrapper(self):
    prefix = r'<Future [\da-f]+ created by '
    @tasklets.tasklet
    @utils.positional(1)
    def foo():
      f1 = tasklets.Future()
      self.assertTrue(re.match(prefix +
                               r'foo\(tasklets_test.py:\d+\); pending>$',
                               repr(f1)),
                      repr(f1))
      f1.set_result(None)
      yield f1
    f2 = foo()
    self.assertTrue(
      re.match(prefix +
               r'testFuture_Repr_TaskletWrapper\(tasklets_test.py:\d+\) '
               r'for tasklet foo\(tasklets_test.py:\d+\).*; pending>$',
               repr(f2)),
      repr(f2))
    f2.check_success()

  def testFuture_Done_State(self):
    f = tasklets.Future()
    self.assertFalse(f.done())
    self.assertEqual(f.state, f.RUNNING)
    f.set_result(42)
    self.assertTrue(f.done())
    self.assertEqual(f.state, f.FINISHING)

  def testFuture_SetResult(self):
    f = tasklets.Future()
    f.set_result(42)
    self.assertEqual(f._result, 42)
    self.assertEqual(f._exception, None)
    self.assertEqual(f.get_result(), 42)

  def testFuture_SetException(self):
    f = tasklets.Future()
    err = RuntimeError(42)
    f.set_exception(err)
    self.assertEqual(f.done(), True)
    self.assertEqual(f._exception, err)
    self.assertEqual(f._result, None)
    self.assertEqual(f.get_exception(), err)
    self.assertRaises(RuntimeError, f.get_result)

  def testFuture_AddDoneCallback_SetResult(self):
    f = tasklets.Future()
    f.add_callback(self.universal_callback, f)
    self.assertEqual(self.log, [])  # Nothing happened yet.
    f.set_result(42)
    eventloop.run()
    self.assertEqual(self.log, [(f,)])

  def testFuture_SetResult_AddDoneCallback(self):
    f = tasklets.Future()
    f.set_result(42)
    self.assertEqual(f.get_result(), 42)
    f.add_callback(self.universal_callback, f)
    eventloop.run()
    self.assertEqual(self.log, [(f,)])

  def testFuture_AddDoneCallback_SetException(self):
    f = tasklets.Future()
    f.add_callback(self.universal_callback, f)
    f.set_exception(RuntimeError(42))
    eventloop.run()
    self.assertEqual(self.log, [(f,)])
    self.assertEqual(f.done(), True)

  def create_futures(self):
    self.futs = []
    for i in range(5):
      f = tasklets.Future()
      f.add_callback(self.universal_callback, f)
      def wake(fut, result):
        fut.set_result(result)
      self.ev.queue_call(i * 0.01, wake, f, i)
      self.futs.append(f)
    return set(self.futs)

  def testFuture_WaitAny(self):
    self.assertEqual(tasklets.Future.wait_any([]), None)
    todo = self.create_futures()
    while todo:
      f = tasklets.Future.wait_any(todo)
      todo.remove(f)
    eventloop.run()
    self.assertEqual(self.log, [(f,) for f in self.futs])

  def testFuture_WaitAll(self):
    todo = self.create_futures()
    tasklets.Future.wait_all(todo)
    self.assertEqual(self.log, [(f,) for f in self.futs])

  def testSleep(self):
    # Ensure that tasklets sleep for the specified amount of time.
    # NOTE: May sleep too long if processor usage is high.
    log = []
    @tasklets.tasklet
    def foo():
      log.append(time.time())
      yield tasklets.sleep(0.1)
      log.append(time.time())
    foo()
    eventloop.run()
    t0, t1 = log
    dt = t1 - t0
    self.assertTrue(0.08 <= dt <= 0.12,
                    'slept too long or too short: dt=%.03f' % dt)

  def testMultiFuture(self):
    @tasklets.tasklet
    def foo(dt):
      yield tasklets.sleep(dt)
      raise tasklets.Return('foo-%s' % dt)
    @tasklets.tasklet
    def bar(n):
      for _ in range(n):
        yield tasklets.sleep(0.01)
      raise tasklets.Return('bar-%d' % n)
    bar5 = bar(5)
    futs = [foo(0.05), foo(0.01), foo(0.03), bar(3), bar5, bar5]
    mfut = tasklets.MultiFuture()
    for fut in futs:
      mfut.add_dependent(fut)
    mfut.complete()
    results = mfut.get_result()
    self.assertEqual(set(results),
                     set(['foo-0.01', 'foo-0.03', 'foo-0.05',
                          'bar-3', 'bar-5']))

  def testMultiFuture_PreCompleted(self):
    @tasklets.tasklet
    def foo():
      yield tasklets.sleep(0.01)
      raise tasklets.Return(42)
    mfut = tasklets.MultiFuture()
    dep = foo()
    dep.wait()
    mfut.add_dependent(dep)
    mfut.complete()
    eventloop.run()
    self.assertTrue(mfut.done())
    self.assertEqual(mfut.get_result(), [42])

  def testMultiFuture_SetException(self):
    mf = tasklets.MultiFuture()
    f1 = tasklets.Future()
    f2 = tasklets.Future()
    f3 = tasklets.Future()
    f2.set_result(2)
    mf.putq(f1)
    f1.set_result(1)
    mf.putq(f2)
    mf.putq(f3)
    mf.putq(4)
    self.ev.run()
    mf.set_exception(ZeroDivisionError())
    f3.set_result(3)
    self.ev.run()
    self.assertRaises(ZeroDivisionError, mf.get_result)

  def testMultiFuture_ItemException(self):
    mf = tasklets.MultiFuture()
    f1 = tasklets.Future()
    f2 = tasklets.Future()
    f3 = tasklets.Future()
    f2.set_result(2)
    mf.putq(f1)
    f1.set_exception(ZeroDivisionError())
    mf.putq(f2)
    mf.putq(f3)
    f3.set_result(3)
    self.ev.run()
    mf.complete()
    self.assertRaises(ZeroDivisionError, mf.get_result)

  def testMultiFuture_Repr(self):
    mf = tasklets.MultiFuture('info')
    r1 = repr(mf)
    mf.putq(1)
    r2 = repr(mf)
    f2 = tasklets.Future()
    f2.set_result(2)
    mf.putq(2)
    r3 = repr(mf)
    self.ev.run()
    r4 = repr(mf)
    f3 = tasklets.Future()
    mf.putq(f3)
    r5 = repr(mf)
    mf.complete()
    r6 = repr(mf)
    f3.set_result(3)
    self.ev.run()
    r7 = repr(mf)
    for r in r1, r2, r3, r4, r5, r6, r7:
      self.assertTrue(
        re.match(
          r'<MultiFuture [\da-f]+ created by '
          r'(testMultiFuture_Repr\(tasklets_test.py:\d+\)|\?) for info; ',
          r))
      if r is r7:
        self.assertTrue('result' in r)
      else:
        self.assertTrue('pending' in r)

  def testQueueFuture(self):
    q = tasklets.QueueFuture()
    @tasklets.tasklet
    def produce_one(i):
      yield tasklets.sleep(i * 0.01)
      raise tasklets.Return(i)
    @tasklets.tasklet
    def producer():
      q.putq(0)
      for i in range(1, 10):
        q.add_dependent(produce_one(i))
      q.complete()
    @tasklets.tasklet
    def consumer():
      for i in range(10):
        val = yield q.getq()
        self.assertEqual(val, i)
      yield q
      self.assertRaises(EOFError, q.getq().get_result)
    @tasklets.tasklet
    def foo():
      yield producer(), consumer()
    foo().get_result()

  def testQueueFuture_Complete(self):
    qf = tasklets.QueueFuture()
    qf.putq(1)
    f2 = tasklets.Future()
    qf.putq(f2)
    self.ev.run()
    g1 = qf.getq()
    g2 = qf.getq()
    g3 = qf.getq()
    f2.set_result(2)
    self.ev.run()
    qf.complete()
    self.ev.run()
    self.assertEqual(g1.get_result(), 1)
    self.assertEqual(g2.get_result(), 2)
    self.assertRaises(EOFError, g3.get_result)
    self.assertRaises(EOFError, qf.getq().get_result)

  def testQueueFuture_SetException(self):
    qf = tasklets.QueueFuture()
    f1 = tasklets.Future()
    f1.set_result(1)
    qf.putq(f1)
    qf.putq(f1)
    self.ev.run()
    qf.putq(2)
    self.ev.run()
    f3 = tasklets.Future()
    f3.set_exception(ZeroDivisionError())
    qf.putq(f3)
    self.ev.run()
    f4 = tasklets.Future()
    qf.putq(f4)
    self.ev.run()
    qf.set_exception(KeyError())
    f4.set_result(4)
    self.ev.run()
    self.assertRaises(KeyError, qf.get_result)
    # Futures are returned in the order of completion, which should be
    # f1, f2, f3, f4.  These produce 1, 2, ZeroDivisionError, 4,
    # respectively.  After that KeyError (the exception set on qf
    # itself) is raised.
    self.assertEqual(qf.getq().get_result(), 1)
    self.assertEqual(qf.getq().get_result(), 2)
    self.assertRaises(ZeroDivisionError, qf.getq().get_result)
    self.assertEqual(qf.getq().get_result(), 4)
    self.assertRaises(KeyError, qf.getq().get_result)
    self.assertRaises(KeyError, qf.getq().get_result)

  def testQueueFuture_SetExceptionAlternative(self):
    qf = tasklets.QueueFuture()
    g1 = qf.getq()
    qf.set_exception(KeyError())
    self.ev.run()
    self.assertRaises(KeyError, g1.get_result)

  def testQueueFuture_ItemException(self):
    qf = tasklets.QueueFuture()
    qf.putq(1)
    f2 = tasklets.Future()
    qf.putq(f2)
    f3 = tasklets.Future()
    f3.set_result(3)
    self.ev.run()
    qf.putq(f3)
    self.ev.run()
    f4 = tasklets.Future()
    f4.set_exception(ZeroDivisionError())
    self.ev.run()
    qf.putq(f4)
    f5 = tasklets.Future()
    qf.putq(f5)
    self.ev.run()
    qf.complete()
    self.ev.run()
    f2.set_result(2)
    self.ev.run()
    f5.set_exception(KeyError())
    self.ev.run()
    # Futures are returned in the order of completion, which should be
    # f1, f3, f4, f2, f5.  These produce 1, 3, ZeroDivisionError, 2,
    # KeyError, respectively.  After that EOFError is raised.
    self.assertEqual(qf.getq().get_result(), 1)
    self.assertEqual(qf.getq().get_result(), 3)
    self.assertRaises(ZeroDivisionError, qf.getq().get_result)
    self.assertEqual(qf.getq().get_result(), 2)
    self.assertRaises(KeyError, qf.getq().get_result)
    self.assertRaises(EOFError, qf.getq().get_result)
    self.assertRaises(EOFError, qf.getq().get_result)

  def testSerialQueueFuture(self):
    q = tasklets.SerialQueueFuture()
    @tasklets.tasklet
    def produce_one(i):
      yield tasklets.sleep(random.randrange(10) * 0.01)
      raise tasklets.Return(i)
    @tasklets.tasklet
    def producer():
      for i in range(10):
        q.add_dependent(produce_one(i))
      q.complete()
    @tasklets.tasklet
    def consumer():
      for i in range(10):
        val = yield q.getq()
        self.assertEqual(val, i)
      yield q
      self.assertRaises(EOFError, q.getq().get_result)
      yield q
    @tasklets.synctasklet
    def foo():
      yield producer(), consumer()
    foo()

  def testSerialQueueFuture_Complete(self):
    sqf = tasklets.SerialQueueFuture()
    g1 = sqf.getq()
    sqf.complete()
    self.assertRaises(EOFError, g1.get_result)

  def testSerialQueueFuture_SetException(self):
    sqf = tasklets.SerialQueueFuture()
    g1 = sqf.getq()
    sqf.set_exception(KeyError())
    self.assertRaises(KeyError, g1.get_result)

  def testSerialQueueFuture_ItemException(self):
    sqf = tasklets.SerialQueueFuture()
    g1 = sqf.getq()
    f1 = tasklets.Future()
    sqf.putq(f1)
    sqf.complete()
    f1.set_exception(ZeroDivisionError())
    self.assertRaises(ZeroDivisionError, g1.get_result)

  def testSerialQueueFuture_PutQ_1(self):
    sqf = tasklets.SerialQueueFuture()
    f1 = tasklets.Future()
    sqf.putq(f1)
    sqf.complete()
    f1.set_result(1)
    self.assertEqual(sqf.getq().get_result(), 1)

  def testSerialQueueFuture_PutQ_2(self):
    sqf = tasklets.SerialQueueFuture()
    sqf.putq(1)
    sqf.complete()
    self.assertEqual(sqf.getq().get_result(), 1)

  def testSerialQueueFuture_PutQ_3(self):
    sqf = tasklets.SerialQueueFuture()
    g1 = sqf.getq()
    sqf.putq(1)
    sqf.complete()
    self.assertEqual(g1.get_result(), 1)

  def testSerialQueueFuture_PutQ_4(self):
    sqf = tasklets.SerialQueueFuture()
    g1 = sqf.getq()
    f1 = tasklets.Future()
    sqf.putq(f1)
    sqf.complete()
    f1.set_result(1)
    self.assertEqual(g1.get_result(), 1)

  def testSerialQueueFuture_GetQ(self):
    sqf = tasklets.SerialQueueFuture()
    sqf.set_exception(KeyError())
    self.assertRaises(KeyError, sqf.getq().get_result)

  def testReducingFuture(self):
    def reducer(arg):
      return sum(arg)
    rf = tasklets.ReducingFuture(reducer, batch_size=10)
    for i in range(10):
      rf.putq(i)
    for i in range(10, 20):
      f = tasklets.Future()
      rf.putq(f)
      f.set_result(i)
    rf.complete()
    self.assertEqual(rf.get_result(), sum(range(20)))

  def testReducingFuture_Empty(self):
    def reducer(_):
      self.fail()
    rf = tasklets.ReducingFuture(reducer)
    rf.complete()
    self.assertEqual(rf.get_result(), None)

  def testReducingFuture_OneItem(self):
    def reducer(_):
      self.fail()
    rf = tasklets.ReducingFuture(reducer)
    rf.putq(1)
    rf.complete()
    self.assertEqual(rf.get_result(), 1)

  def testReducingFuture_ItemException(self):
    def reducer(arg):
      return sum(arg)
    rf = tasklets.ReducingFuture(reducer)
    f1 = tasklets.Future()
    f1.set_exception(ZeroDivisionError())
    rf.putq(f1)
    rf.complete()
    self.assertRaises(ZeroDivisionError, rf.get_result)

  def testReducingFuture_ReducerException_1(self):
    def reducer(arg):
      raise ZeroDivisionError
    rf = tasklets.ReducingFuture(reducer)
    rf.putq(1)
    rf.putq(1)
    rf.complete()
    self.assertRaises(ZeroDivisionError, rf.get_result)

  def testReducingFuture_ReducerException_2(self):
    def reducer(arg):
      raise ZeroDivisionError
    rf = tasklets.ReducingFuture(reducer, batch_size=2)
    rf.putq(1)
    rf.putq(1)
    rf.putq(1)
    rf.complete()
    self.assertRaises(ZeroDivisionError, rf.get_result)

  def testReducingFuture_ReducerFuture_1(self):
    def reducer(arg):
      f = tasklets.Future()
      f.set_result(sum(arg))
      return f
    rf = tasklets.ReducingFuture(reducer, batch_size=2)
    rf.putq(1)
    rf.putq(1)
    rf.complete()
    self.assertEqual(rf.get_result(), 2)

  def testReducingFuture_ReducerFuture_2(self):
    # Weird hack to reach _internal_add_dependent() call in _mark_finished().
    def reducer(arg):
      res = sum(arg)
      if len(arg) < 3:
        f = tasklets.Future()
        f.set_result(res)
        res = f
      return res
    rf = tasklets.ReducingFuture(reducer, batch_size=3)
    rf.putq(1)
    rf.putq(1)
    rf.putq(1)
    rf.putq(1)
    rf.complete()
    self.assertEqual(rf.get_result(), 4)

  def testGetReturnValue(self):
      r0 = tasklets.Return()
      r1 = tasklets.Return(42)
      r2 = tasklets.Return(42, 'hello')
      r3 = tasklets.Return((1, 2, 3))
      self.assertEqual(tasklets.get_return_value(r0), None)
      self.assertEqual(tasklets.get_return_value(r1), 42)
      self.assertEqual(tasklets.get_return_value(r2), (42, 'hello'))
      self.assertEqual(tasklets.get_return_value(r3), (1, 2, 3))

  def testTasklets_Basic(self):
    @tasklets.tasklet
    def t1():
      a = yield t2(3)
      b = yield t3(2)
      raise tasklets.Return(a + b)
    @tasklets.tasklet
    def t2(n):
      raise tasklets.Return(n)
    @tasklets.tasklet
    def t3(n):
      return n
    x = t1()
    self.assertTrue(isinstance(x, tasklets.Future))
    y = x.get_result()
    self.assertEqual(y, 5)

  def testTasklets_Raising(self):
    self.ExpectWarnings()
    @tasklets.tasklet
    def t1():
      f = t2(True)
      try:
        yield f
      except RuntimeError, err:
        self.assertEqual(f.get_exception(), err)
        raise tasklets.Return(str(err))
    @tasklets.tasklet
    def t2(error):
      if error:
        raise RuntimeError('hello')
      else:
        yield tasklets.Future()
    x = t1()
    y = x.get_result()
    self.assertEqual(y, 'hello')

  def testTasklets_YieldRpcs(self):
    @tasklets.tasklet
    def main_tasklet():
      rpc1 = self.conn.async_get(None, [])
      rpc2 = self.conn.async_put(None, [])
      res1 = yield rpc1
      res2 = yield rpc2
      raise tasklets.Return(res1, res2)
    f = main_tasklet()
    result = f.get_result()
    self.assertEqual(result, ([], []))

  def testTasklet_YieldTuple(self):
    @tasklets.tasklet
    def fib(n):
      if n <= 1:
        raise tasklets.Return(n)
      a, b = yield fib(n - 1), fib(n - 2)
      # print 'fib(%r) = %r + %r = %r' % (n, a, b, a + b)
      self.assertTrue(a >= b, (a, b))
      raise tasklets.Return(a + b)
    fut = fib(10)
    val = fut.get_result()
    self.assertEqual(val, 55)

  def testTasklet_YieldTupleError(self):
    @tasklets.tasklet
    def good():
      yield tasklets.sleep(0)
    @tasklets.tasklet
    def bad():
      raise ZeroDivisionError
    @tasklets.tasklet
    def foo():
      try:
        yield good(), bad(), good()
        self.assertFalse('Should have raised ZeroDivisionError')
      except ZeroDivisionError:
        pass
    foo().check_success()

  def testTasklet_YieldTupleTypeError(self):
    self.ExpectWarnings()
    @tasklets.tasklet
    def good():
      yield tasklets.sleep(0)
    @tasklets.tasklet
    def bad():
      raise ZeroDivisionError
      yield tasklets.sleep(0)
    @tasklets.tasklet
    def foo():
      try:
        yield good(), bad(), 42
      except TypeError:
        pass
      else:
        self.assertFalse('Should have raised TypeError')
    foo().check_success()

  def testMultiSingleCombinationYield(self):
    @tasklets.tasklet
    def foo():
      class Test(model.Model):
        k = model.KeyProperty()
        ks = model.KeyProperty(repeated=True)

      t = Test()
      t.put()

      t1 = Test(k=t.key, ks=[t.key, t.key])
      t1.put()

      t1 = t1.key.get()
      obj, objs = yield t1.k.get_async(), model.get_multi_async(t1.ks)
      self.assertEqual(obj.key, t1.k)
      self.assertEqual([obj.key for obj in objs], t1.ks)

    foo().get_result()

  def testAddContextDecorator(self):
    class Demo(object):
      @tasklets.toplevel
      def method(self, arg):
        return tasklets.get_context(), arg

      @tasklets.toplevel
      def method2(self, **kwds):
        return tasklets.get_context(), kwds
    a = Demo()
    old_ctx = tasklets.get_context()
    ctx, arg = a.method(42)
    self.assertTrue(isinstance(ctx, context.Context))
    self.assertEqual(arg, 42)
    self.assertTrue(ctx is not old_ctx)

    old_ctx = tasklets.get_context()
    ctx, kwds = a.method2(foo='bar', baz='ding')
    self.assertTrue(isinstance(ctx, context.Context))
    self.assertEqual(kwds, dict(foo='bar', baz='ding'))
    self.assertTrue(ctx is not old_ctx)


class TracebackTests(test_utils.NDBTest):
  """Checks that errors result in reasonable tracebacks."""

  def testBasicError(self):
    self.ExpectWarnings()
    frames = [sys._getframe()]
    @tasklets.tasklet
    def level3():
      frames.append(sys._getframe())
      raise RuntimeError('hello')
      yield
    @tasklets.tasklet
    def level2():
      frames.append(sys._getframe())
      yield level3()
    @tasklets.tasklet
    def level1():
      frames.append(sys._getframe())
      yield level2()
    @tasklets.tasklet
    def level0():
      frames.append(sys._getframe())
      yield level1()
    fut = level0()
    try:
      fut.check_success()
    except RuntimeError, err:
      _, _, tb = sys.exc_info()
      self.assertEqual(str(err), 'hello')
      tbframes = []
      while tb is not None:
        # It's okay if some _help_tasklet_along frames are present.
        if tb.tb_frame.f_code.co_name != '_help_tasklet_along':
          tbframes.append(tb.tb_frame)
        tb = tb.tb_next
      self.assertEqual(frames, tbframes)
    else:
      self.fail('Expected RuntimeError not raised')


def main():
  unittest.main()


if __name__ == '__main__':
  main()
