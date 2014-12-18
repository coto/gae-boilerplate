import urllib2, urllib, json

class RecaptchaResponse(object):
    def __init__(self, is_valid, error_code=None):
        self.is_valid = is_valid
        self.error_code = error_code

def displayhtml (public_key):
    """Gets the HTML to display for reCAPTCHA

    public_key -- The public api key"""

    return """<script src='https://www.google.com/recaptcha/api.js'></script>
            <div class="g-recaptcha" data-sitekey="%(PublicKey)s"></div>""" % {
        'PublicKey' : public_key
        }

def submit (response_field,
            private_key,
            remoteip):
    """
    Submits a reCAPTCHA request for verification. Returns RecaptchaResponse
    for the request

    response_field -- The value of g-recaptcha-response from the form
    private_key -- your reCAPTCHA private key
    remoteip -- the user's ip address
    """

    if not (response_field):
        return RecaptchaResponse (is_valid = False, error_code = 'incorrect-captcha-sol')


    def encode_if_necessary(s):
        if isinstance(s, unicode):
            return s.encode('utf-8')
        return s

    params = urllib.urlencode ({
        'secret': encode_if_necessary(private_key),
        'remoteip' :  encode_if_necessary(remoteip),
        'response' :  encode_if_necessary(response_field),
        })

    request = urllib2.Request (
        url = "https://www.google.com/recaptcha/api/siteverify",
        data = params
    )

    httpresp = urllib2.urlopen (request)

    return_values = json.loads(httpresp.read ());
    httpresp.close();
    
    if (return_values.get('success')):
        return RecaptchaResponse (is_valid=True)
    else:
        return RecaptchaResponse (is_valid=False, error_code = return_values.get('error_codes', 'unknown error'))