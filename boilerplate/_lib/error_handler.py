# *-* coding: UTF-8 *-*

# standard library imports
import os
import sys
import logging
import traceback
# related third party imports
import webapp2
import httpagentparser
from webapp2_extras import jinja2
from google.appengine.api import app_identity
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
        ua = httpagentparser.detect(request.user_agent)
        _os = ua.has_key('flavor') and 'flavor' or 'os'

        operating_system = str(ua[_os]['name']) if "name" in ua[_os] else "-"
        if 'version' in ua[_os]:
            operating_system += ' ' + str(ua[_os]['version'])
        if 'dist' in ua:
            operating_system += ' ' + str(ua['dist'])

        browser = str(ua['browser']['name']) if 'browser' in ua else "-"
        browser_version = str(ua['browser']['version']) if 'browser' in ua else "-"

        message = '<strong>Application ID:</strong> ' + app_identity.get_application_id() + "<br />" + \
                  '<strong>Application Version:</strong> ' + os.environ['CURRENT_VERSION_ID'] + "<br />" + \
                  '<hr><strong>User Agent:</strong> ' + str(request.user_agent) + "<br />" + \
                  '<strong>IP Address:</strong> ' + str(request.remote_addr) + "<br />" + \
                  '<strong>Operating System:</strong> ' + str(operating_system) + "<br />" + \
                  '<strong>Browser:</strong> ' + str(browser) + "<br />" + \
                  '<strong>Browser Version:</strong> ' + str(browser_version) + "<br />" + \
                  '<hr><strong>Error Type:</strong> ' + exc_type.__name__ + "<br />" + \
                  '<strong>Description:</strong> ' + c['exception'] + "<br />" + \
                  '<strong>Method:</strong> ' + str(os.environ['REQUEST_METHOD']) + "<br />" + \
                  '<strong>URL:</strong> ' + c['url'] + "<br />" + \
                  '<strong>Referer:</strong> ' + str(request.referer) + "<br />" + \
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
