"""
This configuration file loads environment's specific config settings for the application.
It takes precedence over the config located in the boilerplate package.
"""

import os

if "SERVER_SOFTWARE" in os.environ:
    if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
        from config.localhost import config
        config.environment = "localhost"

    elif os.environ['SERVER_SOFTWARE'].startswith('Google'):
        from config.production import config
        config.environment = "production"
else:
    from config.testing import config
    config.environment = "testing"