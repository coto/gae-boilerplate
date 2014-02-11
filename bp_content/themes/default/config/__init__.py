"""
This configuration file loads environment's specific config settings for the application.
It takes precedence over the config located in the boilerplate package.
"""

import os

if 'HTTP_HOST' in os.environ and os.environ['HTTP_HOST'] == "appengine.beecoss.com":
    # Load Boilerplate config only in http://appengine.beecoss.com
    # this code is here just for testing purposes
    from boilerplate import config
elif "SERVER_SOFTWARE" in os.environ:
    if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
        from localhost import config

    elif os.environ['SERVER_SOFTWARE'].startswith('Google'):
        from production import config
    else:
        raise ValueError("Environment undetected")
else:
    from testing import config