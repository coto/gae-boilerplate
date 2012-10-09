app_name = "Google App Engine Boilerplate"

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '_PUT_KEY_HERE_YOUR_SECRET_KEY_',
}
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'boilerplate.models.User',
    'cookie_name': 'session_name'
}
webapp2_config['webapp2_extras.jinja2'] = {
    'template_path': ['templates','boilerplate/templates'],
    'environment_args': {'extensions': ['jinja2.ext.i18n']},
}

# the default language code for the application.
# should match whatever language the site uses when i18n is disabled
app_lang = 'en'

# Locale code = <language>_<territory> (ie 'en_US')
# to pick locale codes see http://cldr.unicode.org/index/cldr-spec/picking-the-right-language-code
# also see http://www.sil.org/iso639-3/codes.asp
# Language codes defined under iso 639-1 http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# Territory codes defined under iso 3166-1 alpha-2 http://en.wikipedia.org/wiki/ISO_3166-1
# disable i18n if locales array is empty or None
locales = ['en_US', 'es_ES', 'it_IT', 'zh_CN', 'id_ID', 'fr_FR', 'de_DE']

contact_sender = "PUT_SENDER_EMAIL_HERE"
contact_recipient = "PUT_RECIPIENT_EMAIL_HERE"

# Password AES Encryption Parameters
aes_key = "12_24_32_BYTES_KEY_FOR_PASSWORDS"
salt = "_PUT_SALT_HERE_TO_SHA512_PASSWORDS_"

# get your own consumer key and consumer secret by registering at https://dev.twitter.com/apps
# callback url must be: http://[YOUR DOMAIN]/login/twitter/complete
twitter_consumer_key = 'PUT_YOUR_TWITTER_CONSUMER_KEY_HERE'
twitter_consumer_secret = 'PUT_YOUR_TWITTER_CONSUMER_SECRET_HERE'

#Facebook Login
# get your own consumer key and consumer secret by registering at https://developers.facebook.com/apps
#Very Important: set the site_url= your domain in the application settings in the facebook app settings page
# callback url must be: http://[YOUR DOMAIN]/login/facebook/complete
_FbApiKey = 'PUT_YOUR_FACEBOOK_PUBLIC_KEY_HERE'
_FbSecret = 'PUT_YOUR_FACEBOOK_PUBLIC_KEY_HERE'

#Linkedin Login
#Get you own api key and secret from https://www.linkedin.com/secure/developer
linkedin_api = 'PUT_YOUR_LINKEDIN_PUBLIC_KEY_HERE'
linkedin_secret = 'PUT_YOUR_LINKEDIN_PUBLIC_KEY_HERE'

# get your own recaptcha keys by registering at http://www.google.com/recaptcha/
captcha_public_key = "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE"
captcha_private_key = "PUT_YOUR_RECAPCHA_PRIVATE_KEY_HERE"

google_analytics_code = "UA-XXXXX-X"

error_templates = {
    403: 'errors/default_error.html',
    404: 'errors/default_error.html',
    500: 'errors/default_error.html',
}

# Enable Federated login (OpenID and OAuth)
# Google App Engine Settings must be set to Authentication Options: Federated Login
enable_federated_login = True

# jinja2 base layout templates
base_layout = 'boilerplate_base.html'

# send error emails to developers
send_mail_developer = True

# fellas' list
DEVELOPERS = (
    ('Santa Klauss', 'snowypal@northpole.com'),
)
