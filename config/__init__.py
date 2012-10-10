import os
from boilerplate.base_config import *

if "SERVER_SOFTWARE" in os.environ:
    if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
        from config.localhost import *

    elif os.environ['SERVER_SOFTWARE'].startswith('Google'):
        from config.production import *
else:
    from config.testing import *