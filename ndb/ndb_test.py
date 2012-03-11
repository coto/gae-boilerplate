"""Run all unittests."""

__author__ = 'Beech Horn'

import sys
import unittest

try:
  import ndb
  location = 'ndb'
except ImportError:
  import google3.third_party.apphosting.python.ndb
  location = 'google3.third_party.apphosting.python.ndb'


def load_tests():
  mods = ['context', 'eventloop', 'key', 'metadata', 'model', 'polymodel',
          'prospective_search', 'query', 'stats', 'tasklets', 'blobstore']
  test_mods = ['%s_test' % name for name in mods]
  ndb = __import__(location, fromlist=test_mods, level=1)

  loader = unittest.TestLoader()
  suite = unittest.TestSuite()

  for mod in [getattr(ndb, name) for name in test_mods]:
    for name in set(dir(mod)):
      if name.endswith('Tests'):
        test_module = getattr(mod, name)
        tests = loader.loadTestsFromTestCase(test_module)
        suite.addTests(tests)

  return suite


def main():
  v = 1
  for arg in sys.argv[1:]:
    if arg.startswith('-v'):
      v += arg.count('v')
    elif arg == '-q':
      v = 0
  result = unittest.TextTestRunner(verbosity=v).run(load_tests())
  sys.exit(not result.wasSuccessful())


if __name__ == '__main__':
  main()
