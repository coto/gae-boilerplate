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

__author__ = 'Kord Campbell'
__website__ = 'http://www.tinyprobe.com'

import oauth_client as oauth2
import simplejson
import logging

# Github OAuth Implementation
class GithubAuth(object):
    
    def __init__(self, github_server, github_client_id, github_client_secret, github_redirect_uri, scope):

        # load github shizzle from config.py
        self.oauth_settings = {
            'client_id': github_client_id,
            'client_secret': github_client_secret,
            'access_token_url': 'https://%s/login/oauth/access_token' % github_server,
            'authorization_url': 'https://%s/login/oauth/authorize' % github_server,
            'redirect_url': '%s' % github_redirect_uri,
            'scope': '%s' % scope
        }

    # get our auth url and return to login handler
    def get_authorize_url(self):
        oauth_client = oauth2.Client( 
            self.oauth_settings['client_id'], 
            self.oauth_settings['client_secret'], 
            self.oauth_settings['authorization_url'] 
        )
        
        authorization_url = oauth_client.authorization_url( 
            redirect_uri=self.oauth_settings['redirect_url'],  
            params={'scope': self.oauth_settings['scope']}
        )

        return authorization_url

    def get_access_token(self, code):
        oauth_client = oauth2.Client(
            self.oauth_settings['client_id'],
            self.oauth_settings['client_secret'],
            self.oauth_settings['access_token_url']
        )
        
        data = oauth_client.access_token(code, self.oauth_settings['redirect_url'])
        
        access_token = data.get('access_token')

        return access_token


    def get_user_info(self, access_token):

        oauth_client = oauth2.Client(
            self.oauth_settings['client_id'],
            self.oauth_settings['client_secret'],
            self.oauth_settings['access_token_url']
        )

        (headers, body) = oauth_client.request(
            'https://api.github.com/user',
            access_token=access_token,
            token_param='access_token'
        )
        return simplejson.loads(body)