import re
import logging
import pytz
from google.appengine.api.urlfetch_errors import DownloadError
from google.appengine.api import urlfetch
from webapp2_extras import i18n
from babel import Locale

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

def get_locale_from_accept_header(request):
    """
    Detect locale from request.header 'Accept-Language'
    Locale with the highest quality factor that most nearly matches our 
    config.locales is returned.
    cls: self object

    Note that in the future if
        all User Agents adopt the convention of sorting quality factors in descending order
        then the first can be taken without needing to parse or sort the accept header
        leading to increased performance
        (see http://lists.w3.org/Archives/Public/ietf-http-wg/2012AprJun/0473.html)
    """
    header = request.headers.get("Accept-Language", '')
    parsed = parse_accept_language_header(header)
    if parsed is None:
        return None
    pairs_sorted_by_q = sorted(parsed.items(), key=lambda (lang, q): q, reverse=True)
    locale = Locale.negotiate([lang for (lang, q) in pairs_sorted_by_q], request.app.config.get('locales'), sep='_')
    return str(locale)


def get_country_code(request):
    """
    Country code based on ISO 3166-1 (http://en.wikipedia.org/wiki/ISO_3166-1)
    :param request: Request Object
    :return: ISO Code of the country
    """
    if 'X-AppEngine-Country' in request.headers:
        if request.headers['X-AppEngine-Country'] in pytz.country_timezones:
            return request.headers['X-AppEngine-Country']
    return None


def get_city_code(request):
    """
    City code based on ISO 3166-1 (http://en.wikipedia.org/wiki/ISO_3166-1)
    :param request: Request Object
    :return: ISO Code of the City
    """
    if 'X-AppEngine-City' in request.headers:
        return request.headers['X-AppEngine-City']
    return None


def get_region_code(request):
    """
    City code based on ISO 3166-1 (http://en.wikipedia.org/wiki/ISO_3166-1)
    :param request: Request Object
    :return: ISO Code of the City
    """
    if 'X-AppEngine-City' in request.headers:
        return request.headers['X-AppEngine-Region']
    return None


def get_city_lat_long(request):
    """
    City code based on ISO 3166-1 (http://en.wikipedia.org/wiki/ISO_3166-1)
    :param request: Request Object
    :return: ISO Code of the City
    """
    if 'X-AppEngine-City' in request.headers:
        return request.headers['X-AppEngine-CityLatLong']
    return None


def set_locale(cls, request, force=None):
    """
    retrieve locale from a prioritized list of sources and then set locale and save it
    cls: self object
    force: a locale to force set (ie 'en_US')
    return: locale as string or None if i18n should be disabled
    """
    locales = cls.app.config.get('locales')
    # disable i18n if config.locales array is empty or None
    if not locales:
        return None
    # 1. force locale if provided
    locale = force
    if locale not in locales:
        # 2. retrieve locale from url query string
        locale = cls.request.get("hl", None)
        if locale not in locales:
            # 3. retrieve locale from cookie
            locale = cls.request.cookies.get('hl', None)
            if locale not in locales:
                # 4. retrieve locale from accept language header
                locale = get_locale_from_accept_header(cls.request)
                if locale not in locales:
                    # 5. detect locale from IP address location
                    territory = get_country_code(request) or 'ZZ'
                    locale = str(Locale.negotiate(territory, locales))
                    if locale not in locales:
                        # 6. use default locale
                        locale = i18n.get_store().default_locale
    i18n.get_i18n().set_locale(locale)
    # save locale in cookie with 26 weeks expiration (in seconds)
    cls.response.set_cookie('hl', locale, max_age = 15724800)
    return locale
