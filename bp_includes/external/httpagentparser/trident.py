"""
Extract client information from http user agent
The module does not try to detect all capabilities of browser in current form (it can easily be extended though).
Tries to
    * be fast
    * very easy to extend
    * reliable enough for practical purposes
    * assist python web apps to detect clients.
"""
import sys

class DetectorsHub(dict):
    _known_types = ['os', 'dist', 'flavor', 'browser']

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        for typ in self._known_types:
            self.setdefault(typ, [])
        self.registerDetectors()

    def register(self, detector):
        if detector.info_type not in self._known_types:
            self[detector.info_type] = [detector]
            self._known_types.insert(detector.order, detector.info_type)
        else:
            self[detector.info_type].append(detector)

    def reorderByPrefs(self, detectors, prefs):
        if prefs is None:
            return []
        elif prefs == []:
            return detectors
        else:
            prefs.insert(0, '')
            return sorted(detectors,
                key=lambda d: d.name in prefs and prefs.index(d.name) or sys.maxsize)

    def __iter__(self):
        return iter(self._known_types)

    def registerDetectors(self):
        detectors = [v() for v in globals().values() if DetectorBase in getattr(v, '__mro__', [])]
        for d in detectors:
            if d.can_register:
                self.register(d)


class DetectorBase(object):
    name = "" # "to perform match in DetectorsHub object"
    info_type = "override me"
    result_key = "override me"
    order = 10 # 0 is highest
    look_for = "string to look for"
    skip_if_found = [] # strings if present stop processin
    can_register = False
    prefs = dict() # dict(info_type = [name1, name2], ..)
    version_markers = [("/", " ")]
    allow_space_in_version = False
    _suggested_detectors = None
    platform = None

    def __init__(self):
        if not self.name:
            self.name = self.__class__.__name__
        self.can_register = (self.__class__.__dict__.get('can_register', True))

    def detect(self, agent, result):
        # -> True/None
        if self.checkWords(agent):
            result[self.info_type] = dict(name=self.name)
            version = self.getVersion(agent)
            if version:
                result[self.info_type]['version'] = version
            if self.platform:
                result['platform'] = {'name': self.platform, 'version': version}
            return True

    def checkWords(self, agent):
        # -> True/None
        for w in self.skip_if_found:
            if w in agent:
                return False
        if self.look_for in agent:
            return True

    def getVersion(self, agent):
        """
        => version string /None
        """
        version_markers = self.version_markers if \
                isinstance(self.version_markers[0], (list, tuple)) else [self.version_markers]
        version_part = agent.split(self.look_for, 1)[-1]
        for start, end in version_markers:
            if version_part.startswith(start) and end in version_part:
                version = version_part[1:]
                if end: # end could be empty string
                    version = version.split(end)[0]
                if not self.allow_space_in_version:
                    version = version.split()[0]
                return version


class OS(DetectorBase):
    info_type = "os"
    can_register = False
    version_markers = [";", " "]
    allow_space_in_version = True
    platform = None


class Dist(DetectorBase):
    info_type = "dist"
    can_register = False
    platform = None


class Flavor(DetectorBase):
    info_type = "flavor"
    can_register = False
    platform = None


class Browser(DetectorBase):
    info_type = "browser"
    can_register = False


class Macintosh(OS):
    look_for = 'Macintosh'
    prefs = dict(dist=None)

    def getVersion(self, agent): pass


class Firefox(Browser):
    look_for = "Firefox"
    version_markers = [('/', '')]
    skip_if_found = ["SeaMonkey"]

class SeaMonkey(Browser):
    look_for = "SeaMonkey"
    version_markers = [('/', '')]


class Konqueror(Browser):
    look_for = "Konqueror"
    version_markers = ["/", ";"]

class OperaMobile(Browser):
    look_for = "Opera Mobi"
    name = "Opera Mobile"
    def getVersion(self, agent):
        try:
            look_for = "Version"
            return agent.split(look_for)[1][1:].split(' ')[0]
        except:
            look_for = "Opera"
            return agent.split(look_for)[1][1:].split(' ')[0]

class Opera(Browser):
    look_for = "Opera"
    def getVersion(self, agent):
        try:
            look_for = "Version"
            return agent.split(look_for)[1][1:].split(' ')[0]
        except:
            look_for = "Opera"
            return agent.split(look_for)[1][1:].split(' ')[0]

class Netscape(Browser):
    look_for = "Netscape"
    version_markers = [("/", '')]

class MSIE(Browser):
    look_for = "MSIE"
    skip_if_found = ["Opera"]
    name = "Microsoft Internet Explorer"
    version_markers = [" ", ";"]

class Trident(Browser):
    look_for = "Trident"
    skip_if_found = ["Opera"]
    name = "Microsoft Internet Explorer"
    version_markers = ["/", ";"]
    trident_to_ie_versions = {
        '4.0': '8.0',
        '5.0': '9.0',
        '6.0': '10.0',
        '7.0': '11.0',
    }
    def getVersion(self, agent):
        return trident_to_ie_versions.get(super(Trident, self).getVersion(agent))


class Galeon(Browser):
    look_for = "Galeon"

class WOSBrowser(Browser):
    look_for = "wOSBrowser"

    def getVersion(self, agent): pass

class Safari(Browser):
    look_for = "Safari"

    def checkWords(self, agent):
        unless_list = ["Chrome", "OmniWeb", "wOSBrowser"]
        if self.look_for in agent:
            for word in unless_list:
                if word in agent:
                    return False
            return True

    def getVersion(self, agent):
        if "Version/" in agent:
            return agent.split('Version/')[-1].split(' ')[0].strip()
        if "Safari/" in agent:
            return agent.split('Safari/')[-1].split(' ')[0].strip()
        else:
            return agent.split('Safari ')[-1].split(' ')[0].strip() # Mobile Safari


class Linux(OS):
    look_for = 'Linux'
    prefs = dict(browser=["Firefox"], dist=["Ubuntu", "Android"], flavor=None)
    platform = 'Linux'

    def getVersion(self, agent): pass

class Blackberry(OS):
    look_for = 'BlackBerry'
    prefs = dict(dist=["BlackberryPlaybook"], flavor=None)
    platform = 'BlackBerry'

    def getVersion(self, agent): pass

class BlackberryPlaybook(Dist):
    look_for = 'PlayBook'
    platform = 'BlackBerry'

    def getVersion(self, agent): pass

class Macintosh(OS):
    look_for = 'Macintosh'
    prefs = dict(dist=None, flavor=['MacOS'])

    def getVersion(self, agent): pass


class MacOS(Flavor):
    look_for = 'Mac OS'
    prefs = dict(browser=['Firefox', 'Opera', "Microsoft Internet Explorer"])
    platform = 'Mac OS'

    def getVersion(self, agent):
        version_end_chars = [';', ')']
        part = agent.split('Mac OS')[-1].strip()
        for c in version_end_chars:
            if c in part:
                version = part.split(c)[0]
                return version.replace('_', '.')
        return ''


class Windows(OS):
    look_for = 'Windows'
    platform = 'Windows'
    prefs = dict(browser=["Microsoft Internet Explorer", 'Firefox'], dict=None, flavor=None)
    win_versions = {
            "NT 6.3": "8.1",
            "NT 6.2": "8",
            "NT 6.1": "7",
            "NT 6.0": "Vista",
            "NT 5.2": "Server 2003 / XP x64",
            "NT 5.1": "XP",
            "NT 5.01": "2000 SP1",
            "NT 5.0": "2000",
            "98; Win 9x 4.90": "Me"
        }

    def getVersion(self, agent):
        v = agent.split('Windows')[-1].split(';')[0].strip()
        if ')' in v:
            v = v.split(')')[0]
        v = self.win_versions.get(v, v)
        return v


class Ubuntu(Dist):
    look_for = 'Ubuntu'
    version_markers = ["/", " "]
    prefs = dict(browser=['Firefox'])


class Debian(Dist):
    look_for = 'Debian'
    version_markers = ["/", " "]
    prefs = dict(browser=['Firefox'])


class Chrome(Browser):
    look_for = "Chrome"
    version_markers = ["/", " "]
    def getVersion(self, agent):
        part = agent.split(self.look_for + self.version_markers[0])[-1]
        version = part.split(self.version_markers[1])[0]
        if '+' in version:
            version = part.split('+')[0]
        return version.strip()

class ChromeiOS(Browser):
    look_for = "CriOS"
    version_markers = ["/", " "]

class ChromeOS(OS):
    look_for = "CrOS"
    platform = ' ChromeOS'
    version_markers = [" ", " "]
    prefs = dict(browser=['Chrome'])
    def getVersion(self, agent):
        version_markers = self.version_markers
        if self.look_for + '+' in agent:
            version_markers = ['+', '+']
        return agent.split(self.look_for + version_markers[0])[-1].split(version_markers[1])[1].strip()[:-1]

class Android(Dist):
    look_for = 'Android'
    prefs = dict(browser=['Safari'])
    platform = 'Android'

    def getVersion(self, agent):
        return agent.split(self.look_for)[-1].split(';')[0].strip()

class WebOS(Dist):
    look_for = 'hpwOS'

    def getVersion(self, agent):
        return agent.split('hpwOS/')[-1].split(';')[0].strip()


class IPhone(Dist):
    look_for = 'iPhone'
    prefs = dict(browser=['Safari'])
    platform = 'iOS'

    def getVersion(self, agent):
        version_end_chars = [';', ')']
        part = agent.split('Mac OS')[-1].strip()
        for c in version_end_chars:
            if c in part:
                version = part.split(c)[0]
                return version.replace('_', '.')

class IPad(Dist):
    look_for = 'iPad; CPU OS'
    prefs = dict(browser=['Safari'])
    version_markers = [(' ', ' ')]
    allow_space_in_version = False
    platform = 'iOS'

    def getVersion(self, agent):
        version = super(Dist, self).getVersion(agent)
        return version.replace('_', '.')

detectorshub = DetectorsHub()


def detect(agent, fill_none=False):
    """
    fill_none: if name/version is not detected respective key is still added to the result with value None
    """
    result = dict(platform=dict(name=None, version=None))
    _suggested_detectors = []

    for info_type in detectorshub:
        detectors = _suggested_detectors or detectorshub[info_type]
        for detector in detectors:
            try:
                ret = detector.detect(agent, result)
            except Exception as err:
                ret = False
            if ret:
                if detector.prefs and not detector._suggested_detectors:
                    _suggested_detectors = detectorshub.reorderByPrefs(detectors, detector.prefs.get(info_type))
                    detector._suggested_detectors = _suggested_detectors
                    break

    if fill_none:
        attrs_d = {'name': None, 'version': None}
        for key in ('os', 'browser'):
            if key not in result:
                result[key] = attrs_d
            else:
                for k, v in attrs_d.items():
                    result[k] = v

    return result


def simple_detect(agent):
    """
    -> (os, browser) # tuple of strings
    """
    result = detect(agent)
    os_list = []
    if 'flavor' in result: os_list.append(result['flavor']['name'])
    if 'dist' in result: os_list.append(result['dist']['name'])
    if 'os' in result: os_list.append(result['os']['name'])

    os = os_list and " ".join(os_list) or "Unknown OS"
    os_version = os_list and (result.get('flavor') and result['flavor'].get('version')) or (
    result.get('dist') and result['dist'].get('version')) or (result.get('os') and result['os'].get('version')) or ""
    browser = 'browser' in result and result['browser'].get('name') or 'Unknown Browser'
    browser_version = 'browser' in result and result['browser'].get('version') or ""
    if browser_version:
        browser = " ".join((browser, browser_version))
    if os_version:
        os = " ".join((os, os_version))
    return os, browser
