

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '_PUT_KEY_HERE_YOUR_SECRET_KEY_',
    }
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'models.models.User',
    'cookie_name': 'session_name'
}

contact_recipient = "PUT_YOUR_EMAIL_HERE"

# get your own recaptcha keys by registering at www.google.com/recaptcha
captcha_public_key = "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE"
captcha_private_key = "PUT_YOUR_RECAPCHA_PRIVATE_KEY_HERE"

google_analytics_code = "UA-XXXXX-X"

