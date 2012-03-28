"""Some tests for datastore_rpc.py."""

import unittest

from .google_imports import apiproxy_stub_map
from .google_imports import datastore_rpc

from . import model
from . import test_utils


class PendingTests(test_utils.NDBTest):
  """Tests for the 'pending RPC' management."""

  def testBasicSetup1(self):
    ent = model.Expando()
    ent.foo = 'bar'
    rpc = self.conn.async_put(None, [ent])
    [key] = rpc.get_result()
    self.assertEqual(key, model.Key(flat=['Expando', 1]))

  def testBasicSetup2(self):
    key = model.Key(flat=['Expando', 1])
    rpc = self.conn.async_get(None, [key])
    [ent] = rpc.get_result()
    self.assertTrue(ent is None)

  def SetUpCallHooks(self):
    self.pre_args = []
    self.post_args = []
    apiproxy_stub_map.apiproxy.GetPreCallHooks().Append('test1',
                                                        self.PreCallHook)
    apiproxy_stub_map.apiproxy.GetPostCallHooks().Append('test1',
                                                         self.PostCallHook)

  def PreCallHook(self, service, call, request, response, rpc=None):
    self.pre_args.append((service, call, request, response, rpc))

  def PostCallHook(self, service, call, request, response,
                   rpc=None, error=None):
    self.post_args.append((service, call, request, response, rpc, error))

  def testCallHooks(self):
    self.SetUpCallHooks()
    key = model.Key(flat=['Expando', 1])
    rpc = self.conn.async_get(None, [key])
    self.assertEqual(len(self.pre_args), 1)
    self.assertEqual(self.post_args, [])
    [ent] = rpc.get_result()
    self.assertTrue(ent is None)
    self.assertEqual(len(self.pre_args), 1)
    self.assertEqual(len(self.post_args), 1)
    self.assertEqual(self.pre_args[0][:2], ('datastore_v3', 'Get'))
    self.assertEqual(self.post_args[0][:2], ('datastore_v3', 'Get'))

  def testCallHooks_Pending(self):
    self.SetUpCallHooks()
    key = model.Key(flat=['Expando', 1])
    rpc = self.conn.async_get(None, [key])
    self.conn.wait_for_all_pending_rpcs()
    self.assertEqual(rpc.state, 2)  # FINISHING
    self.assertEqual(len(self.pre_args), 1)
    self.assertEqual(len(self.post_args), 1)  # NAILED IT!
    self.assertEqual(self.conn.get_pending_rpcs(), set())

  def NastyCallback(self, rpc):
    rpc.get_result()
    key = model.Key(flat=['Expando', 1])
    self.conn.async_get(None, [key])

  def testCallHooks_Pending_CallbackAddsMore(self):
    self.SetUpCallHooks()
    conf = datastore_rpc.Configuration(on_completion=self.NastyCallback)
    key = model.Key(flat=['Expando', 1])
    self.conn.async_get(conf, [key])
    self.conn.wait_for_all_pending_rpcs()
    self.assertEqual(self.conn.get_pending_rpcs(), set())


def main():
  unittest.main()


if __name__ == '__main__':
  main()
