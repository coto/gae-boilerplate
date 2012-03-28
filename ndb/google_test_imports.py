"""Like google_imports.py, but for use by tests.

This imports the testbed package and some stubs.
"""

from . import google_imports

if google_imports.normal_environment:
  from google.appengine.api.prospective_search import prospective_search_stub
  from google.appengine.datastore import datastore_stub_util
  from google.appengine.ext import testbed
else:
  # Prospective search is optional.
  try:
    from google3.apphosting.api.prospective_search import prospective_search_stub
  except ImportError:
    pass
  from google3.apphosting.datastore import datastore_stub_util
  from google3.apphosting.ext import testbed
