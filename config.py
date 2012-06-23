
app_name = "Google App Engine Boilerplate"
app_version = "2.0 RC2"

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '_PUT_KEY_HERE_YOUR_SECRET_KEY_',
    }
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'models.models.User',
    'cookie_name': 'session_name'
}

contact_sender = "PUT_SENDER_EMAIL_HERE"
contact_recipient = "PUT_RECIPIENT_EMAIL_HERE"

salt = "_PUT_SALT_HERE_TO_SHA512_PASSWORDS_"

# get your own consumer key and consumer secret by registering at https://dev.twitter.com/apps
twitter_consumer_key = 'PUT_YOUR_TWITTER_CONSUMER_KEY_HERE'
twitter_consumer_secret = 'PUT_YOUR_TWITTER_CONSUMER_SECRET_HERE'

# get your own recaptcha keys by registering at www.google.com/recaptcha
captcha_public_key = "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE"
captcha_private_key = "PUT_YOUR_RECAPCHA_PRIVATE_KEY_HERE"

google_analytics_code = "UA-XXXXX-X"

error_templates = {
    404: 'errors/default_error.html',
    500: 'errors/default_error.html',
}
