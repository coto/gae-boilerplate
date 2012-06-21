
boilerplate_version = "Google App Engine Boilerplate 2.0 RC1"

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '_PUT_KEY_HERE_YOUR_SECRET_KEY_',
}
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'models.models.User',
    'cookie_name': 'session_name'
}
webapp2_config['webapp2_extras.jinja2'] = {
    'template_path': 'templates',
    'environment_args': {'extensions': ['jinja2.ext.i18n']},
}

contact_recipient = "PUT_YOUR_EMAIL_HERE"

salt = "_PUT_SALT_HERE_TO_SHA512_PASSWORDS_"

# get your own recaptcha keys by registering at www.google.com/recaptcha
captcha_public_key = "PUT_YOUR_RECAPCHA_PUBLIC_KEY_HERE"
captcha_private_key = "PUT_YOUR_RECAPCHA_PRIVATE_KEY_HERE"

google_analytics_code = "UA-XXXXX-X"

error_templates = {
    404: 'errors/default_error.html',
    500: 'errors/default_error.html',
}
