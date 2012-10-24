import os
import re
import random
import hashlib
import string
import unicodedata
from datetime import datetime, timedelta
import Cookie
import webapp2

def random_string(size=6, chars=string.ascii_letters + string.digits):
    """ Generate random string """
    return ''.join(random.choice(chars) for _ in range(size))

def hashing(plaintext, salt=""):
    """ Returns the hashed and encrypted hexdigest of a plaintext and salt"""
    app = webapp2.get_app()

    # Hashing (sha512)
    plaintext = "%s@%s" % (plaintext, salt)
    phrase_digest = hashlib.sha512(plaintext.encode('UTF-8')).hexdigest()

    # Encryption (PyCrypto)
    # wow... it's so secure :)
    try:
        from Crypto.Cipher import AES
        mode = AES.MODE_CBC

        # We can not generate random initialization vector because is difficult to retrieve them later without knowing
        # a priori the hash to match. We take 16 bytes from the hexdigest to make the vectors different for each hashed
        # plaintext.
        iv = phrase_digest[:16]
        encryptor = AES.new(app.config.get('aes_key'), mode,iv)
        ciphertext = [encryptor.encrypt(chunk) for chunk in chunks(phrase_digest, 16)]
        return ''.join(ciphertext)
    except (ImportError, NameError), e:
        import logging
        logging.error("CRYPTO is not running")
        return phrase_digest

def chunks(list, size):
    """ Yield successive sized chunks from list. """

    for i in xrange(0, len(list), size):
        yield list[i:i+size]

def encode(plainText):
    num = 0
    key = "0123456789abcdefghijklmnopqrstuvwxyz"
    key += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for c in plainText: num = (num << 8) + ord(c)
    encodedMsg = ""
    while num > 0:
        encodedMsg = key[num % len(key)] + encodedMsg
        num /= len(key)
    return encodedMsg

def decode(encodedMsg):
    num = 0
    key = "0123456789abcdefghijklmnopqrstuvwxyz"
    key += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for c in encodedMsg: num = num * len(key) + key.index(c)
    text = ""
    while num > 0:
        text = chr(num % 256) + text
        num /= 256
    return text

def write_cookie(cls, COOKIE_NAME, COOKIE_VALUE, path, expires=7200):
    """
    Write a cookie
    @path = could be a cls.request.path to set a specific path
    @expires = seconds (integer) to expire the cookie, by default 2 hours ()
    expires = 7200 # 2 hours
    expires = 1209600 # 2 weeks
    expires = 2629743 # 1 month
    """

    # days, seconds, then other fields.
    time_expire = datetime.now() + timedelta(seconds=expires)
    time_expire = time_expire.strftime("%a, %d-%b-%Y %H:%M:%S GMT")

    cls.response.headers.add_header(
        'Set-Cookie', COOKIE_NAME+'='+COOKIE_VALUE+'; expires='+str(time_expire)+'; path='+path+'; HttpOnly')
    return

def read_cookie(cls, name):
    """ Use: cook.read(cls, COOKIE_NAME) """

    string_cookie = os.environ.get('HTTP_COOKIE', '')
    cls.cookie = Cookie.SimpleCookie()
    cls.cookie.load(string_cookie)
    value = None
    if cls.cookie.get(name):
        value  = cls.cookie[name].value

    return value

def get_date_time(format="%Y-%m-%d %H:%M:%S", UTC_OFFSET=3):
    """
    Get date and time in UTC with a specific format
     By default it UTC = -3 (Chilean Time)
    """

    local_datetime = datetime.now()
    now = local_datetime - timedelta(hours=UTC_OFFSET)
    if format != "datetimeProperty":
        now = now.strftime(format)
    #    now = datetime.fromtimestamp(1321925140.78)
    return now

EMAIL_REGEXP = "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,4}|[0-9]{1,3})(\\]?)$"

def is_email_valid(email):
    if len(email) > 7:
        if re.match(EMAIL_REGEXP, email) != None:
            return 1
    return 0

ALPHANUMERIC_REGEXP = "^\w+$"

def is_alphanumeric(field):
    if re.match(ALPHANUMERIC_REGEXP, field) is not None:
        return 1
    return 0

def get_device(cls):
    # TODO: Remove this function
    uastring = cls.request.user_agent or 'unknown'
    is_mobile = (("Mobile" in uastring and "Safari" in uastring) or\
                 ("Windows Phone OS" in uastring and "IEMobile" in uastring) or\
                 ("Blackberry") in uastring)

    if "MSIE" in uastring:
        browser = "Explorer"
    elif "Firefox" in uastring:
        browser = "Firefox"
    elif "Presto" in uastring:
        browser = "Opera"
    elif "Android" in uastring and "AppleWebKit" in uastring:
        browser = "Chrome for andriod"
    elif "iPhone" in uastring and "AppleWebKit" in uastring:
        browser = "Safari for iPhone"
    elif "iPod" in uastring and "AppleWebKit" in uastring:
        browser = "Safari for iPod"
    elif "iPad" in uastring and "AppleWebKit" in uastring:
        browser = "Safari for iPad"
    elif "Chrome" in uastring:
        browser = "Chrome"
    elif "AppleWebKit" in uastring:
        browser = "Safari"
    else:
        browser = "unknown"

    device = {
        "is_mobile": is_mobile,
        "browser": browser,
        "uastring": uastring
    }
    return device

def set_device_cookie_and_return_bool(cls, force=""):
    """
    set a cookie for device (dvc) returning a dict and set cookie
    Cookie value has to be "mobile" or "desktop" string
    """

    if force != "":
        # force cookie to param
        device_cookie = force
    elif cls.request.get("device") == "":
        # ask for cookie of device
        device_cookie = str(read_cookie(cls, "dvc"))
        if not device_cookie or device_cookie == "None" or device_cookie == "":
            # If cookie has an error, check which device is been used
            if get_device(cls)["is_mobile"]:
                device_cookie = "mobile"
            else:
                device_cookie = "desktop"
    else:
        # set cookie to param 'is_mobile' value directly
        device_cookie = cls.request.get("device")

    # Set Cookie for Two weeks with 'device_cookie' value
    write_cookie(cls, "dvc", str(device_cookie), "/", 1209600)
    return device_cookie == "mobile"

def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-ascii characters,
    and converts spaces to hyphens.  For use in urls and filenames

    From Django's "django/template/defaultfilters.py".
    """
    _slugify_strip_re = re.compile(r'[^\w\s-]')
    _slugify_hyphenate_re = re.compile(r'[-\s]+')

    if not isinstance(value, unicode):
        value = unicode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(_slugify_strip_re.sub('', value).strip().lower())
    return _slugify_hyphenate_re.sub('-', value)

# TODO: Use locale (Babel)
COUNTRIES = [
    ("", ""),
    ("AF", "Afghanistan"),
    ("AL", "Albania"),
    ("DZ", "Algeria"),
    ("AS", "American Samoa"),
    ("AD", "Andorra"),
    ("AG", "Angola"),
    ("AI", "Anguilla"),
    ("AG", "Antigua & Barbuda"),
    ("AR", "Argentina"),
    ("AA", "Armenia"),
    ("AW", "Aruba"),
    ("AU", "Australia"),
    ("AT", "Austria"),
    ("AZ", "Azerbaijan"),
    ("BS", "Bahamas"),
    ("BH", "Bahrain"),
    ("BD", "Bangladesh"),
    ("BB", "Barbados"),
    ("BY", "Belarus"),
    ("BE", "Belgium"),
    ("BZ", "Belize"),
    ("BJ", "Benin"),
    ("BM", "Bermuda"),
    ("BT", "Bhutan"),
    ("BO", "Bolivia"),
    ("BL", "Bonaire"),
    ("BA", "Bosnia & Herzegovina"),
    ("BW", "Botswana"),
    ("BR", "Brazil"),
    ("BC", "British Indian Ocean Ter"),
    ("BN", "Brunei"),
    ("BG", "Bulgaria"),
    ("BF", "Burkina Faso"),
    ("BI", "Burundi"),
    ("KH", "Cambodia"),
    ("CM", "Cameroon"),
    ("CA", "Canada"),
    ("IC", "Canary Islands"),
    ("CV", "Cape Verde"),
    ("KY", "Cayman Islands"),
    ("CF", "Central African Republic"),
    ("TD", "Chad"),
    ("CD", "Channel Islands"),
    ("CL", "Chile"),
    ("CN", "China"),
    ("CI", "Christmas Island"),
    ("CS", "Cocos Island"),
    ("CO", "Colombia"),
    ("CC", "Comoros"),
    ("CG", "Congo"),
    ("CK", "Cook Islands"),
    ("CR", "Costa Rica"),
    ("CT", "Cote D'Ivoire"),
    ("HR", "Croatia"),
    ("CU", "Cuba"),
    ("CB", "Curacao"),
    ("CY", "Cyprus"),
    ("CZ", "Czech Republic"),
    ("DK", "Denmark"),
    ("DJ", "Djibouti"),
    ("DM", "Dominica"),
    ("DO", "Dominican Republic"),
    ("TM", "East Timor"),
    ("EC", "Ecuador"),
    ("EG", "Egypt"),
    ("SV", "El Salvador"),
    ("GQ", "Equatorial Guinea"),
    ("ER", "Eritrea"),
    ("EE", "Estonia"),
    ("ET", "Ethiopia"),
    ("FA", "Falkland Islands"),
    ("FO", "Faroe Islands"),
    ("FJ", "Fiji"),
    ("FI", "Finland"),
    ("FR", "France"),
    ("GF", "French Guiana"),
    ("PF", "French Polynesia"),
    ("FS", "French Southern Ter"),
    ("GA", "Gabon"),
    ("GM", "Gambia"),
    ("GE", "Georgia"),
    ("DE", "Germany"),
    ("GH", "Ghana"),
    ("GI", "Gibraltar"),
    ("GB", "Great Britain"),
    ("GR", "Greece"),
    ("GL", "Greenland"),
    ("GD", "Grenada"),
    ("GP", "Guadeloupe"),
    ("GU", "Guam"),
    ("GT", "Guatemala"),
    ("GN", "Guinea"),
    ("GY", "Guyana"),
    ("HT", "Haiti"),
    ("HW", "Hawaii"),
    ("HN", "Honduras"),
    ("HK", "Hong Kong"),
    ("HU", "Hungary"),
    ("IS", "Iceland"),
    ("IN", "India"),
    ("ID", "Indonesia"),
    ("IA", "Iran"),
    ("IQ", "Iraq"),
    ("IR", "Ireland"),
    ("IM", "Isle of Man"),
    ("IL", "Israel"),
    ("IT", "Italy"),
    ("JM", "Jamaica"),
    ("JP", "Japan"),
    ("JO", "Jordan"),
    ("KZ", "Kazakhstan"),
    ("KE", "Kenya"),
    ("KI", "Kiribati"),
    ("NK", "Korea North"),
    ("KS", "Korea South"),
    ("KW", "Kuwait"),
    ("KG", "Kyrgyzstan"),
    ("LA", "Laos"),
    ("LV", "Latvia"),
    ("LB", "Lebanon"),
    ("LS", "Lesotho"),
    ("LR", "Liberia"),
    ("LY", "Libya"),
    ("LI", "Liechtenstein"),
    ("LT", "Lithuania"),
    ("LU", "Luxembourg"),
    ("MO", "Macau"),
    ("MK", "Macedonia"),
    ("MG", "Madagascar"),
    ("MY", "Malaysia"),
    ("MW", "Malawi"),
    ("MV", "Maldives"),
    ("ML", "Mali"),
    ("MT", "Malta"),
    ("MH", "Marshall Islands"),
    ("MQ", "Martinique"),
    ("MR", "Mauritania"),
    ("MU", "Mauritius"),
    ("ME", "Mayotte"),
    ("MX", "Mexico"),
    ("MI", "Midway Islands"),
    ("MD", "Moldova"),
    ("MC", "Monaco"),
    ("MN", "Mongolia"),
    ("MS", "Montserrat"),
    ("MA", "Morocco"),
    ("MZ", "Mozambique"),
    ("MM", "Myanmar"),
    ("NA", "Nambia"),
    ("NU", "Nauru"),
    ("NP", "Nepal"),
    ("AN", "Netherland Antilles"),
    ("NL", "Netherlands (Holland, Europe)"),
    ("NV", "Nevis"),
    ("NC", "New Caledonia"),
    ("NZ", "New Zealand"),
    ("NI", "Nicaragua"),
    ("NE", "Niger"),
    ("NG", "Nigeria"),
    ("NW", "Niue"),
    ("NF", "Norfolk Island"),
    ("NO", "Norway"),
    ("OM", "Oman"),
    ("PK", "Pakistan"),
    ("PW", "Palau Island"),
    ("PS", "Palestine"),
    ("PA", "Panama"),
    ("PG", "Papua New Guinea"),
    ("PY", "Paraguay"),
    ("PE", "Peru"),
    ("PH", "Philippines"),
    ("PO", "Pitcairn Island"),
    ("PL", "Poland"),
    ("PT", "Portugal"),
    ("PR", "Puerto Rico"),
    ("QA", "Qatar"),
    ("ME", "Republic of Montenegro"),
    ("RS", "Republic of Serbia"),
    ("RE", "Reunion"),
    ("RO", "Romania"),
    ("RU", "Russia"),
    ("RW", "Rwanda"),
    ("NT", "St Barthelemy"),
    ("EU", "St Eustatius"),
    ("HE", "St Helena"),
    ("KN", "St Kitts-Nevis"),
    ("LC", "St Lucia"),
    ("MB", "St Maarten"),
    ("PM", "St Pierre & Miquelon"),
    ("VC", "St Vincent & Grenadines"),
    ("SP", "Saipan"),
    ("SO", "Samoa"),
    ("AS", "Samoa American"),
    ("SM", "San Marino"),
    ("ST", "Sao Tome & Principe"),
    ("SA", "Saudi Arabia"),
    ("SN", "Senegal"),
    ("SC", "Seychelles"),
    ("SL", "Sierra Leone"),
    ("SG", "Singapore"),
    ("SK", "Slovakia"),
    ("SI", "Slovenia"),
    ("SB", "Solomon Islands"),
    ("OI", "Somalia"),
    ("ZA", "South Africa"),
    ("ES", "Spain"),
    ("LK", "Sri Lanka"),
    ("SD", "Sudan"),
    ("SR", "Suriname"),
    ("SZ", "Swaziland"),
    ("SE", "Sweden"),
    ("CH", "Switzerland"),
    ("SY", "Syria"),
    ("TA", "Tahiti"),
    ("TW", "Taiwan"),
    ("TJ", "Tajikistan"),
    ("TZ", "Tanzania"),
    ("TH", "Thailand"),
    ("TG", "Togo"),
    ("TK", "Tokelau"),
    ("TO", "Tonga"),
    ("TT", "Trinidad & Tobago"),
    ("TN", "Tunisia"),
    ("TR", "Turkey"),
    ("TU", "Turkmenistan"),
    ("TC", "Turks & Caicos Is"),
    ("TV", "Tuvalu"),
    ("UG", "Uganda"),
    ("UA", "Ukraine"),
    ("AE", "United Arab Emirates"),
    ("GB", "United Kingdom"),
    ("US", "United States of America"),
    ("UY", "Uruguay"),
    ("UZ", "Uzbekistan"),
    ("VU", "Vanuatu"),
    ("VS", "Vatican City State"),
    ("VE", "Venezuela"),
    ("VN", "Vietnam"),
    ("VB", "Virgin Islands (Brit)"),
    ("VA", "Virgin Islands (USA)"),
    ("WK", "Wake Island"),
    ("WF", "Wallis & Futana Is"),
    ("YE", "Yemen"),
    ("ZR", "Zaire"),
    ("ZM", "Zambia"),
    ("ZW", "Zimbabwe")]
