"""
    A pytz version that runs smoothly on Google App Engine.

    Based on http://appengine-cookbook.appspot.com/recipe/caching-pytz-helper/

    To use, add pytz to your path normally, but import it from the gae module:

        from pytz.gae import pytz

    Applied patches:

      - The zoneinfo dir is removed from pytz, as this module includes a ziped
        version of it.

      - pytz is monkey patched to load zoneinfos from a zipfile.

      - pytz is patched to not check all zoneinfo files when loaded. This is
        sad, I wish that was lazy, so it could be monkey patched. As it is,
        the zipfile patch doesn't work and it'll spend resources checking
        hundreds of files that we know aren't there.

    pytz caches loaded zoneinfos, and this module will additionally cache them
    in memcache to avoid unzipping constantly. The cache key includes the
    OLSON_VERSION so it is invalidated when pytz is updated.
"""
import os
import logging
import pytz
import zipfile
from cStringIO import StringIO

# Fake memcache for when we're not running under the SDK, likely a script.
class memcache(object):
    @classmethod
    def add(*args, **kwargs):
        pass

    @classmethod
    def get(*args, **kwargs):
        return None

try:
    # Don't use memcache outside of Google App Engine or with GAE's dev server.
    if not os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
        from google.appengine.api import memcache
except ImportError:
    pass

zoneinfo = None
zoneinfo_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
    'zoneinfo.zip'))


def get_zoneinfo():
    """Cache the opened zipfile in the module."""
    global zoneinfo
    if zoneinfo is None:
        zoneinfo = zipfile.ZipFile(zoneinfo_path)

    return zoneinfo

available = {}

def open_resource(name):
    """Opens a resource from the zoneinfo subdir for reading."""
    name_parts = name.lstrip('/').split('/')
    if os.path.pardir in name_parts:
        raise ValueError('Bad path segment: %r' % os.path.pardir)

    cache_key = 'pytz.zoneinfo.%s.%s' % (pytz.OLSON_VERSION, name)
    zonedata = memcache.get(cache_key)
    if zonedata is None:
        zonedata = get_zoneinfo().read('zoneinfo/' + '/'.join(name_parts))
        memcache.add(cache_key, zonedata)
        logging.info('Added timezone to memcache: %s' % cache_key)
    else:
        logging.info('Loaded timezone from memcache: %s' % cache_key)

    return StringIO(zonedata)

def resource_exists(name):
    """Return true if the given resource exists"""
    if name not in available:
        try:
            get_zoneinfo().getinfo('zoneinfo/' + name)
            available[name] = True
        except KeyError:
            available[name] = False

    return available[name]


pytz.open_resource = open_resource
pytz.resource_exists = resource_exists
