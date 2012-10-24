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

__author__  = 'Rodrigo Augosto (@coto)'
__website__ = 'www.beecoss.com'

import os, sys
# Third party libraries path must be fixed before importing webapp2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'boilerplate/external'))

import webapp2

import routes
from boilerplate import routes as boilerplate_routes
from boilerplate import base_config as boilerplate_config
import config
from boilerplate.lib.basehandler import handle_error

webapp2_config = boilerplate_config.config
webapp2_config.update(config.config)

app = webapp2.WSGIApplication(debug = os.environ['SERVER_SOFTWARE'].startswith('Dev'), config=webapp2_config)

app.error_handlers[403] = handle_error
app.error_handlers[404] = handle_error
if not app.debug:
    app.error_handlers[500]    = handle_error
    app.config['send_mail_developer'] = False

routes.add_routes(app)
boilerplate_routes.add_routes(app)


