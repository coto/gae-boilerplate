# *-* coding: UTF-8 *-*

# standard library imports
import traceback
import logging
import sys
# related third party imports
import webapp2
from webapp2_extras import jinja2
from google.appengine.api import taskqueue
# local application/library specific imports


def handle_error(request, response, exception):
    exc_type, exc_value, exc_tb = sys.exc_info()

    c = {
        'exception': str(exception),
        'url': request.url,
    }

    if request.app.config.get('send_mail_developer') is not False:
        # send email
        subject = "[{}] ERROR {}".format(request.app.config.get('environment').upper(),
                                         request.app.config.get('app_name'))

        lines = traceback.format_exception(exc_type, exc_value, exc_tb)

        message = '<strong>app_name:</strong> ' + request.app.config.get('app_name') + "<br />" + \
                  '<strong>Referer:</strong> ' + str(request.referer) + "<br />" + \
                  '<strong>Type:</strong> ' + exc_type.__name__ + "<br />" + \
                  '<strong>Description:</strong> ' + c['exception'] + "<br />" + \
                  '<strong>URL:</strong> ' + c['url'] + "<br />" + \
                  '<strong>Traceback:</strong> <br />' + '<br />'.join(lines)

        if c['exception'] is not 'Error saving Email Log in datastore':
            email_url = webapp2.uri_for('taskqueue-send-email')

            for dev in request.app.config.get('developers'):
                taskqueue.add(url=email_url, params={
                    'to': dev[1],
                    'subject': subject,
                    'body': message,
                    'sender': request.app.config.get('contact_sender'),
                })

    status_int = hasattr(exception, 'status_int') and exception.status_int or 500
    template = request.app.config.get('error_templates')[status_int]
    t = jinja2.get_jinja2(app=webapp2.get_app()).render_template(template, **c)
    logging.error("Error {}: {}".format(status_int, exception))
    response.write(t)
    response.set_status(status_int)
