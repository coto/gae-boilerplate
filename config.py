

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '_PUT_KEY_HERE_YOUR_SECRET_KEY_',
    }
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'models.User',
    'cookie_name': 'session_name'
}
