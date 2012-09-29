from google.appengine.ext.appstats import recording

def webapp_add_wsgi_middleware(app):
    app = recording.appstats_wsgi_middleware(app)
    return app
