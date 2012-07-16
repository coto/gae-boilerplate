from lib.oauth2 import Consumer as OAuthConsumer, Token, Request as OAuthRequest, \
                   SignatureMethod_HMAC_SHA1
from urllib2 import Request, urlopen
from lib import simplejson
import config

# Twitter configuration
TWITTER_SERVER = 'api.twitter.com'
TWITTER_REQUEST_TOKEN_URL = 'https://%s/oauth/request_token' % TWITTER_SERVER
TWITTER_ACCESS_TOKEN_URL = 'https://%s/oauth/access_token' % TWITTER_SERVER
# Note: oauth/authorize forces the user to authorize every time.
#       oauth/authenticate uses their previous selection, barring revocation.
TWITTER_AUTHORIZATION_URL = 'http://%s/oauth/authenticate' % TWITTER_SERVER
TWITTER_CHECK_AUTH = 'https://twitter.com/account/verify_credentials.json'

class TwitterAuth(object):
    """Twitter OAuth authentication mechanism"""
    AUTHORIZATION_URL = TWITTER_AUTHORIZATION_URL
    REQUEST_TOKEN_URL = TWITTER_REQUEST_TOKEN_URL
    ACCESS_TOKEN_URL = TWITTER_ACCESS_TOKEN_URL
    SERVER_URL = TWITTER_SERVER
    AUTH_BACKEND_NAME = 'twitter'
    SETTINGS_KEY_NAME = 'TWITTER_CONSUMER_KEY'
    SETTINGS_SECRET_NAME = 'TWITTER_CONSUMER_SECRET'
    
    def __init__(self, request, redirect_uri=None):
        """Init method"""
        self.request = request
        self.redirect_uri = redirect_uri
    
    def auth_url(self):
        """Return redirect url"""
        token = self.unauthorized_token()
        name = self.AUTH_BACKEND_NAME + 'unauthorized_token_name'
        self.request.session[name] = token.to_string()
        return str(self.oauth_request(token, self.AUTHORIZATION_URL).to_url())
    
    def auth_complete(self, oauth_token, oauth_verifier):
        """Return user, might be logged in"""
        name = self.AUTH_BACKEND_NAME + 'unauthorized_token_name'
        unauthed_token = self.request.session[name]
        del self.request.session[name]
        if not unauthed_token:
            raise ValueError('Missing unauthorized token')

        token = Token.from_string(unauthed_token)
        if token.key != oauth_token:
            raise ValueError('Incorrect tokens')

        access_token = self.access_token(token, oauth_verifier)
        
        data = self.user_data(access_token)
        return data
    
    def save_association_data(self, user_data):
        name = self.AUTH_BACKEND_NAME + 'association_data'
        self.request.session[name] = simplejson.dumps(user_data)
        
    def get_association_data(self):
        name = self.AUTH_BACKEND_NAME + 'association_data'
        if name in self.request.session:
            association_data = simplejson.loads(self.request.session[name])
            del self.request.session[name]
        else:
            association_data = None
        return association_data
    
    def unauthorized_token(self):
        """Return request for unauthorized token (first stage)"""
        request = self.oauth_request(token=None, url=self.REQUEST_TOKEN_URL)
        response = self.fetch_response(request)
        return Token.from_string(response)
    
    def oauth_request(self, token, url, oauth_verifier=None, extra_params=None):
        """Generate OAuth request, setups callback url"""
        params = {}
        if self.redirect_uri:
            params['oauth_callback'] = self.redirect_uri
        if extra_params:
            params.update(extra_params)

        if oauth_verifier:
            params['oauth_verifier'] = oauth_verifier
        request = OAuthRequest.from_consumer_and_token(self.consumer,
                                                       token=token,
                                                       http_url=url,
                                                       parameters=params)
        request.sign_request(SignatureMethod_HMAC_SHA1(), self.consumer, token)
        return request
    
    def fetch_response(self, request):
        """Executes request and fetchs service response"""
        response = urlopen(request.to_url())
        return '\n'.join(response.readlines())
    
    def access_token(self, token, oauth_verifier):
        """Return request for access token value"""
        request = self.oauth_request(token, self.ACCESS_TOKEN_URL, oauth_verifier)
        return Token.from_string(self.fetch_response(request))
    
    def user_data(self, access_token):
        """Return user data provided"""
        request = self.oauth_request(access_token, TWITTER_CHECK_AUTH)
        json = self.fetch_response(request)
        try:
            return simplejson.loads(json)
        except ValueError:
            return None
    
    @property
    def consumer(self):
        """Setups consumer"""
        return OAuthConsumer(*self.get_key_and_secret())

    def get_key_and_secret(self):
        """Return tuple with Consumer Key and Consumer Secret for current
        service provider. Must return (key, secret), order *must* be respected.
        """
        return config.twitter_consumer_key, config.twitter_consumer_secret