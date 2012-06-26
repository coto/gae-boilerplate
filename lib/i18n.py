import re
import logging
from lib import utils
from google.appengine.api.urlfetch_errors import DownloadError
from google.appengine.api import urlfetch
from webapp2_extras import i18n

# Locale code = <language>_<territory> (ie 'en_US')
# Language codes defined under iso 639-1 http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# Territory codes defined under iso 3166-1 alpha-2 http://en.wikipedia.org/wiki/ISO_3166-1
# Available locales should be in descending priority order.  ie the first entry is default and if 
# there are for example en_US followed by en_GB then en_US will take priority 
# if the language detected is english byt territory could not be detected
AVAILABLE_LOCALES = ['en_US', 'es_ES', 'it_IT', 'zh_CN', 'id_ID']
LANGUAGES = {
             'en_US': 'English',
             'es_ES': 'Spanish',
             'it_IT': 'Italian',
             'zh_CN': 'Chinese',
             'id_ID': 'Indonesian'
             }

def parse_accept_language_header(string, pattern='([a-zA-Z]{1,8}(-[a-zA-Z0-9]{1,8})?)\s*(;\s*q\s*=\s*(1|0\.[0-9]+))?'):
    """
    Parse a dict from an Accept-Language header string
    (see http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html)
    example input: en-US,en;q=0.8,es-es;q=0.5
    example output: {'en_US': 100, 'en': 80, 'es_ES': 50}
    """
    res = {}
    if not string: return None
    for match in re.finditer(pattern, string):
        if None == match.group(4):
            q = 1
        else:
            q = match.group(4)
        l = match.group(1).replace('-','_')
        if len(l) == 2:
            l = l.lower()
        elif len(l) == 5:
            l = l.split('_')[0].lower() + "_" + l.split('_')[1].upper()
        else:
            l = None
        if l:
            res[l] = int(100*float(q))
    return res

def get_territory_from_ip(cls):
    """
    Detect the territory code derived from IP Address location
    Returns US, CA, CL, AR, etc.
    cls: self object
    
    Uses lookup service http://geoip.wtanaka.com/cc/<ip>
    You can get a flag image given the returned territory 
        with http://geoip.wtanaka.com/flag/<territory>.gif
        example: http://geoip.wtanaka.com/flag/us.gif
    """
    territory = None
    try:
        result = urlfetch.fetch("http://geoip.wtanaka.com/cc/"+cls.request.remote_addr)
        if result.status_code == 200:
            fetch = result.content
            if len(str(fetch)) < 3:
                territory = str(fetch).upper()
            else:
                logging.warning("Ups, geoip.wtanaka.com is not working. Look what it returns: "+ str(fetch) )
        else:
            logging.warning("Ups, geoip.wtanaka.com is not working. Status Code: "+ str(result.status_code) )
    except DownloadError:
        logging.warning("Couldn't resolve http://geoip.wtanaka.com/cc/"+cls.request.remote_addr)
    return territory

def get_locale_from_territory(territory):
    """
    Returns locale from AVAILABLE_LOCALES given a territory code
    """
    available_territories = [locale.split('_')[1] for locale in AVAILABLE_LOCALES]
    for i,t in enumerate(available_territories):
        if t == territory:
            return AVAILABLE_LOCALES[i]

def get_locale_from_accept_header(cls):
    """
    Detect locale from request.header 'Accept-Language'
    Locale with the highest quality factor that most nearly matches our 
    AVAILABLE_LOCALES is returned.
    cls: self object

    Note that in the future if
        all User Agents adopt the convention of sorting quality factors in descending order
        then the first can be taken without needing to parse or sort the accept header
        leading to increased performance
        (see http://lists.w3.org/Archives/Public/ietf-http-wg/2012AprJun/0473.html)
    """
    available_languages = [locale.split('_')[0] for locale in AVAILABLE_LOCALES]
    header = cls.request.headers.get("Accept-Language", '')
    parsed = parse_accept_language_header(header)
    for item in sorted(parsed.iteritems()):
        if item[0] in AVAILABLE_LOCALES:
            return item[0]
        for i,l in enumerate(available_languages):
            if item[0] == l:
                return AVAILABLE_LOCALES[i]

def set_locale(cls, force=None):
    """
    retrieve locale from a prioritized list of sources and then set locale and save it
    cls: self object
    force: a locale to force set (ie 'en_US')
    return: locale
    """
    # 1. force locale if provided
    locale = force
    if locale not in AVAILABLE_LOCALES:
        # 2. retrieve locale from url query string
        locale = cls.request.get("hl", None)
        if locale not in AVAILABLE_LOCALES:
            # 3. retrieve locale from cookie
            locale = utils.read_cookie(cls, "hl")
            if locale not in AVAILABLE_LOCALES:
                # 4. retrieve locale from accept language header
                locale = get_locale_from_accept_header(cls)
                if locale not in AVAILABLE_LOCALES:
                    # 5. detect locale from IP address location
                    locale = get_locale_from_territory(get_territory_from_ip(cls))
                    if locale not in AVAILABLE_LOCALES:
                        # 6. use default locale
                        locale = AVAILABLE_LOCALES[0]
    # convert unicode locale to string for headers
    locale = str(locale)
    i18n.get_i18n().set_locale(locale)
    # save locale in cookie with 26 weeks expiration (in seconds)
    utils.write_cookie(cls, "hl", locale, "/", 15724800)
    return locale

def get_language(locale):
    return LANGUAGES[locale]

def get_territory_code(locale):
    return locale.split('_')[1]