#!/usr/bin/env python
##
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'Rodrigo Augosto (@coto)'
__website__ = 'www.beecoss.com'

import os
import sys
# Third party libraries path must be fixed before importing webapp2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bp_includes/external'))

import webapp2


from bp_includes.lib.error_handler import handle_error
from bp_includes import config as config_boilerplate

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bp_content/themes/', os.environ['theme']))
# Import Config Importing
import config as config_theme

# Routes Importing
from bp_admin import routes as routes_admin
from bp_includes import routes as routes_boilerplate
import routes as routes_theme


webapp2_config = config_boilerplate.config
webapp2_config.update(config_theme.config)

app = webapp2.WSGIApplication(debug=os.environ['SERVER_SOFTWARE'].startswith('Dev'), config=webapp2_config)

if not app.debug:
    for status_int in app.config['error_templates']:
        app.error_handlers[status_int] = handle_error

routes_theme.add_routes(app)
routes_boilerplate.add_routes(app)
routes_admin.add_routes(app)
