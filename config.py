

webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': '[ PUT KEY HERE YOUR SECRET KEY ]',
    }
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'models.User',
    'cookie_name': 'session_name'
}
